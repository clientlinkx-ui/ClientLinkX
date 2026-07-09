CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TYPE "BusinessType" AS ENUM ('RETAIL', 'HOSPITALITY');
CREATE TYPE "TransactionType" AS ENUM ('PAYMENT', 'REFUND', 'LOYALTY_ADJUSTMENT');
CREATE TYPE "TransactionStatus" AS ENUM ('PENDING', 'COMPLETED', 'FAILED');

CREATE TABLE "Business" (
  "id" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "businessType" "BusinessType" NOT NULL,
  "primaryLanguage" TEXT NOT NULL DEFAULT 'en',
  "locationGeo" TEXT NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "Business_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "User" (
  "id" TEXT NOT NULL,
  "phone" TEXT NOT NULL,
  "name" TEXT,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "CustomerLoyalty" (
  "id" TEXT NOT NULL,
  "businessId" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "pointsBalance" INTEGER NOT NULL DEFAULT 0,
  "stampCount" INTEGER NOT NULL DEFAULT 0,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "CustomerLoyalty_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "Transaction" (
  "id" TEXT NOT NULL,
  "businessId" TEXT NOT NULL,
  "userId" TEXT NOT NULL,
  "paymentProvider" TEXT,
  "providerOrderId" TEXT,
  "providerPaymentId" TEXT,
  "amount" DECIMAL(12,2) NOT NULL,
  "currency" TEXT NOT NULL DEFAULT 'INR',
  "transactionType" "TransactionType" NOT NULL,
  "status" "TransactionStatus" NOT NULL DEFAULT 'PENDING',
  "pointsEarned" INTEGER NOT NULL DEFAULT 0,
  "metadata" JSONB NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Transaction_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "Campaign" (
  "id" TEXT NOT NULL,
  "businessId" TEXT NOT NULL,
  "header" TEXT NOT NULL,
  "isActive" BOOLEAN NOT NULL DEFAULT true,
  "triggerRadius" DOUBLE PRECISION NOT NULL,
  "messageBody" JSONB NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "Campaign_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "User_phone_key" ON "User"("phone");
CREATE UNIQUE INDEX "CustomerLoyalty_businessId_userId_key" ON "CustomerLoyalty"("businessId", "userId");
CREATE INDEX "CustomerLoyalty_userId_idx" ON "CustomerLoyalty"("userId");
CREATE INDEX "Transaction_businessId_createdAt_idx" ON "Transaction"("businessId", "createdAt");
CREATE INDEX "Transaction_userId_idx" ON "Transaction"("userId");
CREATE INDEX "Campaign_businessId_isActive_idx" ON "Campaign"("businessId", "isActive");

ALTER TABLE "CustomerLoyalty"
  ADD CONSTRAINT "CustomerLoyalty_businessId_fkey"
  FOREIGN KEY ("businessId") REFERENCES "Business"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "CustomerLoyalty"
  ADD CONSTRAINT "CustomerLoyalty_userId_fkey"
  FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "Transaction"
  ADD CONSTRAINT "Transaction_businessId_fkey"
  FOREIGN KEY ("businessId") REFERENCES "Business"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "Transaction"
  ADD CONSTRAINT "Transaction_userId_fkey"
  FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "Campaign"
  ADD CONSTRAINT "Campaign_businessId_fkey"
  FOREIGN KEY ("businessId") REFERENCES "Business"("id") ON DELETE CASCADE ON UPDATE CASCADE;
