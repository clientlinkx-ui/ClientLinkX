const { Worker } = require("bullmq");
const axios = require("axios");
const config = require("../config");
const { connection } = require("../queues/whatsappQueue");

function resolveLocalizedMessage(messageBody, primaryLanguage) {
  if (!messageBody || typeof messageBody !== "object") {
    throw new Error("messageBody must be a language-to-text object");
  }

  return messageBody[primaryLanguage] || messageBody.en;
}

const worker = new Worker(
  "whatsapp-notifications",
  async (job) => {
    const { user, business, campaign } = job.data;
    const text = resolveLocalizedMessage(campaign.messageBody, business.primaryLanguage);

    if (!text) {
      throw new Error(`No WhatsApp message for campaign ${campaign.id}`);
    }

    if (!config.metaAccessToken || !config.metaPhoneNumberId) {
      throw new Error("META_ACCESS_TOKEN and META_PHONE_NUMBER_ID are required");
    }

    const endpoint = `https://graph.facebook.com/v20.0/${config.metaPhoneNumberId}/messages`;

    try {
      await axios.post(
        endpoint,
        {
          messaging_product: "whatsapp",
          recipient_type: "individual",
          to: user.phone,
          type: "text",
          text: {
            preview_url: false,
            body: text
          }
        },
        {
          headers: {
            Authorization: `Bearer ${config.metaAccessToken}`,
            "Content-Type": "application/json"
          },
          timeout: 10000
        }
      );
    } catch (error) {
      const response = error.response && error.response.data;
      console.error("WhatsApp notification failed", {
        jobId: job.id,
        campaignId: campaign.id,
        businessId: business.id,
        response: response || error.message
      });
      throw error;
    }
  },
  {
    connection,
    concurrency: Number(process.env.WHATSAPP_WORKER_CONCURRENCY || 10)
  }
);

worker.on("completed", (job) => {
  console.log(`WhatsApp notification job ${job.id} completed`);
});

worker.on("failed", (job, error) => {
  console.error(`WhatsApp notification job ${job && job.id} failed`, error);
});
