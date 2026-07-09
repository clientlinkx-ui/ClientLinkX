const fp = require("fastify-plugin");
const fastifyJwt = require("@fastify/jwt");
const config = require("../config");

async function authPlugin(fastify) {
  if (!config.jwtSecret) {
    throw new Error("JWT_SECRET_KEY is required");
  }

  await fastify.register(fastifyJwt, {
    secret: config.jwtSecret
  });

  fastify.decorate("authenticate", async function authenticate(request) {
    await request.jwtVerify();
  });

  fastify.decorate("verifyRole", function verifyRole(allowedRoles) {
    return async function roleGuard(request) {
      await request.jwtVerify();

      const role = request.user && request.user.role;
      if (!allowedRoles.includes(role)) {
        const error = new Error("Forbidden");
        error.statusCode = 403;
        throw error;
      }
    };
  });
}

module.exports = fp(authPlugin, {
  name: "auth-plugin"
});
