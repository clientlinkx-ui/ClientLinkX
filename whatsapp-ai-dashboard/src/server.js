const crypto = require("crypto");
const Fastify = require("fastify");
const cors = require("@fastify/cors");
const rawBody = require("fastify-raw-body");
const { Decimal } = require("@prisma/client/runtime/library");
const config = require("./config");
const prisma = require("./prisma");
const authPlugin = require("./plugins/auth");
const ProximityService = require("./services/proximityService");
const { connection, whatsappQueue } = require("./queues/whatsappQueue");

const fastify = Fastify({
  logger: true
});

const proximityService = new ProximityService(prisma);

function toNumber(value) {
  if (value instanceof Decimal) {
    return value.toNumber();
  }
  return Number(value || 0);
}

function verifyRazorpaySignature(rawPayload, signature) {
  if (!config.razorpayKeySecret) {
    throw new Error("RAZORPAY_KEY_SECRET is required");
  }

  if (!signature) {
    return false;
  }

  const expected = crypto
    .createHmac("sha256", config.razorpayKeySecret)
    .update(rawPayload)
    .digest("hex");

  const expectedBuffer = Buffer.from(expected);
  const actualBuffer = Buffer.from(signature);

  return (
    expectedBuffer.length === actualBuffer.length &&
    crypto.timingSafeEqual(expectedBuffer, actualBuffer)
  );
}

async function buildServer() {
  await fastify.register(cors, {
    origin(origin, callback) {
      if (!origin || config.corsOrigins.includes(origin)) {
        callback(null, true);
        return;
      }
      callback(new Error("CORS origin denied"), false);
    },
    credentials: true
  });

  await fastify.register(rawBody, {
    field: "rawBody",
    global: false,
    encoding: false,
    runFirst: true
  });

  await fastify.register(authPlugin);

  fastify.post(
    "/api/v1/location/ping",
    {
      preHandler: fastify.verifyRole(["CUSTOMER", "MERCHANT"]),
      schema: {
        body: {
          type: "object",
          required: ["userId", "phone", "latitude", "longitude"],
          properties: {
            userId: { type: "string", minLength: 1 },
            phone: { type: "string", minLength: 8 },
            latitude: { type: "number", minimum: -90, maximum: 90 },
            longitude: { type: "number", minimum: -180, maximum: 180 }
          }
        }
      }
    },
    async (request, reply) => {
      const { userId, phone, latitude, longitude } = request.body;
      const matches = await proximityService.findActiveCampaignsForLocation(latitude, longitude);
      const queued = [];

      for (const match of matches) {
        const dedupeKey = `notify:${match.businessId}:${userId}:${match.campaignId}`;
        const acquired = await connection.set(dedupeKey, "1", "EX", 3600, "NX");

        if (!acquired) {
          continue;
        }

        const job = await whatsappQueue.add(
          "send-campaign-message",
          {
            user: { id: userId, phone },
            business: {
              id: match.businessId,
              name: match.businessName,
              businessType: match.businessType,
              primaryLanguage: match.primaryLanguage
            },
            campaign: {
              id: match.campaignId,
              header: match.header,
              messageBody: match.messageBody
            },
            distanceMeters: toNumber(match.distanceMeters)
          },
          {
            jobId: `${dedupeKey}:${Math.floor(Date.now() / 3600000)}`
          }
        );

        queued.push({
          jobId: job.id,
          businessId: match.businessId,
          campaignId: match.campaignId,
          distanceMeters: toNumber(match.distanceMeters)
        });
      }

      return reply.code(202).send({
        matchedCampaigns: matches.length,
        queuedNotifications: queued
      });
    }
  );

  fastify.get(
    "/api/v1/dashboard/metrics",
    {
      preHandler: fastify.verifyRole(["MERCHANT"]),
      schema: {
        querystring: {
          type: "object",
          required: ["businessId"],
          properties: {
            businessId: { type: "string", minLength: 1 }
          }
        }
      }
    },
    async (request) => {
      const { businessId } = request.query;
      const where = { businessId, status: "COMPLETED" };

      const [
        revenueAggregate,
        loyaltyCount,
        recentTransactions,
        repeatGroups,
        platformTransactions
      ] = await Promise.all([
        prisma.transaction.aggregate({
          where,
          _sum: { amount: true },
          _avg: { amount: true }
        }),
        prisma.customerLoyalty.count({ where: { businessId } }),
        prisma.transaction.findMany({
          where,
          orderBy: { createdAt: "desc" },
          take: 5,
          include: {
            user: {
              select: { id: true, phone: true, name: true }
            }
          }
        }),
        prisma.transaction.groupBy({
          by: ["userId"],
          where,
          _count: { userId: true },
          having: {
            userId: {
              _count: {
                gt: 1
              }
            }
          }
        }),
        prisma.transaction.findMany({
          where,
          select: {
            amount: true,
            metadata: true
          }
        })
      ]);

      const totalRevenue = toNumber(revenueAggregate._sum.amount);
      const averageBillingValue = toNumber(revenueAggregate._avg.amount);
      const repeatCustomerCount = repeatGroups.length;
      const retentionRatePercentage =
        loyaltyCount === 0 ? 0 : Number(((repeatCustomerCount / loyaltyCount) * 100).toFixed(2));

      const counterQrRevenue = platformTransactions
        .filter((transaction) => transaction.metadata && transaction.metadata.platform === "counter_qr_engagement_saas")
        .reduce((sum, transaction) => sum + toNumber(transaction.amount), 0);

      return {
        businessId,
        totalRevenue,
        averageBillingValue,
        uniqueLoyaltyProfiles: loyaltyCount,
        repeatCustomerCount,
        retentionRatePercentage,
        counterQrEngagementSaasRevenue: Number(counterQrRevenue.toFixed(2)),
        recentTransactions
      };
    }
  );

  fastify.post(
    "/api/v1/webhooks/razorpay",
    {
      config: {
        rawBody: true
      }
    },
    async (request, reply) => {
      const signature = request.headers["x-razorpay-signature"];
      const rawPayload = request.rawBody || Buffer.from(JSON.stringify(request.body));

      if (!verifyRazorpaySignature(rawPayload, signature)) {
        return reply.code(401).send({ error: "Invalid Razorpay signature" });
      }

      const event = request.body;

      if (event.event !== "order.paid") {
        return { received: true, ignored: true };
      }

      const order = event.payload && event.payload.order && event.payload.order.entity;
      if (!order) {
        return reply.code(400).send({ error: "Missing order payload" });
      }

      const notes = order.notes || {};
      const businessId = notes.businessId;
      const userId = notes.userId;

      if (!businessId || !userId) {
        return reply.code(400).send({ error: "Missing businessId or userId in order notes" });
      }

      const amount = new Decimal(Number(order.amount_paid || order.amount || 0) / 100);
      const pointsEarned = Number(notes.pointsEarned || Math.floor(amount.toNumber()));
      const stampIncrement = Number(notes.stampIncrement || 1);

      const result = await prisma.$transaction(async (tx) => {
        const ledger = await tx.transaction.create({
          data: {
            businessId,
            userId,
            paymentProvider: "razorpay",
            providerOrderId: order.id,
            providerPaymentId: order.payment_id || null,
            amount,
            currency: order.currency || "INR",
            transactionType: "PAYMENT",
            status: "COMPLETED",
            pointsEarned,
            metadata: {
              platform: notes.platform || "counter_qr_engagement_saas",
              razorpayOrder: order
            }
          }
        });

        const loyalty = await tx.customerLoyalty.upsert({
          where: {
            businessId_userId: {
              businessId,
              userId
            }
          },
          create: {
            businessId,
            userId,
            pointsBalance: pointsEarned,
            stampCount: stampIncrement
          },
          update: {
            pointsBalance: {
              increment: pointsEarned
            },
            stampCount: {
              increment: stampIncrement
            }
          }
        });

        return { ledger, loyalty };
      });

      return reply.code(201).send({
        received: true,
        transactionId: result.ledger.id,
        loyaltyId: result.loyalty.id
      });
    }
  );

  fastify.get("/health", async () => ({ ok: true }));

  return fastify;
}

if (require.main === module) {
  buildServer()
    .then((server) => server.listen({ port: config.port, host: "0.0.0.0" }))
    .catch((error) => {
      fastify.log.error(error);
      process.exit(1);
    });
}

module.exports = buildServer;
