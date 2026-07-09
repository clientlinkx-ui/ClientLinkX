const prisma = require("../prisma");

class ProximityService {
  constructor(client = prisma) {
    this.prisma = client;
  }

  async findActiveCampaignsForLocation(latitude, longitude) {
    const lat = Number(latitude);
    const lng = Number(longitude);

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      throw new Error("Invalid latitude or longitude");
    }

    return this.prisma.$queryRaw`
      SELECT
        c.id AS "campaignId",
        c.header,
        c."triggerRadius",
        c."messageBody",
        b.id AS "businessId",
        b.name AS "businessName",
        b."businessType",
        b."primaryLanguage",
        b."locationGeo",
        ST_Distance(
          ST_SetSRID(ST_MakePoint(${lng}, ${lat}), 4326)::geography,
          ST_SetSRID(
            ST_MakePoint(
              split_part(b."locationGeo", ',', 2)::double precision,
              split_part(b."locationGeo", ',', 1)::double precision
            ),
            4326
          )::geography
        ) AS "distanceMeters"
      FROM "Campaign" c
      INNER JOIN "Business" b ON b.id = c."businessId"
      WHERE c."isActive" = true
        AND b."locationGeo" ~ '^-?[0-9]+(\\.[0-9]+)?,-?[0-9]+(\\.[0-9]+)?$'
        AND ST_Distance(
          ST_SetSRID(ST_MakePoint(${lng}, ${lat}), 4326)::geography,
          ST_SetSRID(
            ST_MakePoint(
              split_part(b."locationGeo", ',', 2)::double precision,
              split_part(b."locationGeo", ',', 1)::double precision
            ),
            4326
          )::geography
        ) <= c."triggerRadius"
      ORDER BY "distanceMeters" ASC;
    `;
  }
}

module.exports = ProximityService;
