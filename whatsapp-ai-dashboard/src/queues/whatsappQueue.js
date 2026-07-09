const { Queue } = require("bullmq");
const IORedis = require("ioredis");
const config = require("../config");

const connection = new IORedis(config.redisUrl, {
  maxRetriesPerRequest: null
});

const whatsappQueue = new Queue("whatsapp-notifications", {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: {
      type: "exponential",
      delay: 5000
    },
    removeOnComplete: 1000,
    removeOnFail: 5000
  }
});

module.exports = {
  connection,
  whatsappQueue
};
