require("dotenv").config();

const env = process.env;

module.exports = {
  port: Number(env.PORT || 3000),
  databaseUrl: env.DATABASE_URL,
  redisUrl: env.REDIS_URL || "redis://localhost:6379",
  jwtSecret: env.JWT_SECRET_KEY,
  razorpayKeySecret: env.RAZORPAY_KEY_SECRET,
  metaAccessToken: env.META_ACCESS_TOKEN,
  metaPhoneNumberId: env.META_PHONE_NUMBER_ID,
  corsOrigins: [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://yourloyaltysaas.com",
    "https://app.yourloyaltysaas.com",
    "https://api.yourloyaltysaas.com"
  ]
};
