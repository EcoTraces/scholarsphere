"use strict";

const {onCall, HttpsError} = require("firebase-functions/v2/https");
const {onDocumentWritten} = require("firebase-functions/v2/firestore");
const {initializeApp} = require("firebase-admin/app");
const {getAuth} = require("firebase-admin/auth");
const {FieldValue, getFirestore} = require("firebase-admin/firestore");

initializeApp();

const managedRoles = new Set([
  "opportunityProvider",
  "verificationOfficer",
  "moderator",
  "supportOfficer",
  "administrator",
  "securityAdministrator",
  "superAdministrator",
]);

const allRoles = new Set(["applicant", ...managedRoles]);

function requireAdministrator(request) {
  const role = request.auth && request.auth.token.role;
  if (!["administrator", "superAdministrator"].includes(role)) {
    throw new HttpsError(
        "permission-denied",
        "An authorized administrator is required.",
    );
  }
  return request.auth;
}

function canAssignRole(actorRole, targetRole) {
  if (actorRole === "superAdministrator") return managedRoles.has(targetRole);
  return actorRole === "administrator" && [
    "opportunityProvider",
    "verificationOfficer",
    "moderator",
    "supportOfficer",
  ].includes(targetRole);
}

function requiredString(value, field) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new HttpsError("invalid-argument", `${field} is required.`);
  }
  return value.trim();
}

exports.createManagedUser = onCall(async (request) => {
  const administrator = requireAdministrator(request);
  const fullName = requiredString(request.data.fullName, "fullName");
  const email = requiredString(request.data.email, "email").toLowerCase();
  const password = requiredString(
      request.data.temporaryPassword,
      "temporaryPassword",
  );
  const role = requiredString(request.data.role, "role");

  if (!managedRoles.has(role)) {
    throw new HttpsError("invalid-argument", "The selected role is invalid.");
  }
  if (!canAssignRole(administrator.token.role, role)) {
    throw new HttpsError(
        "permission-denied",
        "Only a super administrator can assign privileged administrator roles.",
    );
  }
  if (password.length < 12) {
    throw new HttpsError(
        "invalid-argument",
        "The temporary password must contain at least 12 characters.",
    );
  }

  let user;
  try {
    user = await getAuth().createUser({
      email,
      password,
      displayName: fullName,
      emailVerified: true,
      disabled: false,
    });
    await getAuth().setCustomUserClaims(user.uid, {role});
    const account = {
      uid: user.uid,
      fullName,
      email,
      role,
      status: "active",
      emailVerified: true,
      twoFactorEnabled: false,
      marketingEmailsEnabled: false,
      deadlineNotificationsEnabled: true,
    };
    await getFirestore().collection("users").doc(user.uid).set({
      ...account,
      createdAt: FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
      createdBy: administrator.uid,
      requiresPasswordChange: true,
    });
    return account;
  } catch (error) {
    if (user) await getAuth().deleteUser(user.uid);
    if (error.code === "auth/email-already-exists") {
      throw new HttpsError(
          "already-exists",
          "An account already exists for this email.",
      );
    }
    console.error("createManagedUser failed", error);
    throw new HttpsError("internal", "The account could not be created.");
  }
});

exports.suspendUser = onCall(async (request) => {
  const administrator = requireAdministrator(request);
  const userId = requiredString(request.data.userId, "userId");
  if (userId === administrator.uid) {
    throw new HttpsError(
        "failed-precondition",
        "You cannot suspend your own account.",
    );
  }
  await getAuth().updateUser(userId, {disabled: true});
  await getFirestore().collection("users").doc(userId).update({
    status: "suspended",
    suspendedBy: administrator.uid,
    suspendedAt: FieldValue.serverTimestamp(),
    updatedAt: FieldValue.serverTimestamp(),
  });
  await getAuth().revokeRefreshTokens(userId);
  return {userId, status: "suspended"};
});

// Keeps each user's Firebase Auth custom claim (`role`, read by
// firestore.rules' isAdministrator() and the FastAPI backend's
// get_current_user()) in sync with their `users/{userId}` document -
// the only source of truth the client UI actually reads for routing.
// Without this, any role set outside createManagedUser (a direct
// Firestore edit, a future admin UI, a data migration) leaves the
// account routed to the right dashboard by the client while every real
// data request 403s, because the token backing those requests still
// carries no role (or a stale one). Fires on every write rather than
// diffing old/new values - `setCustomUserClaims` is idempotent and cheap
// against the low, per-user write rate this collection sees, and this
// also repairs documents that already existed before this trigger was
// deployed, the next time they're touched.
exports.syncUserRoleClaim = onDocumentWritten(
    "users/{userId}",
    async (event) => {
      const after = event.data && event.data.after;
      if (!after || !after.exists) return;
      const role = after.data().role;
      if (!allRoles.has(role)) {
        console.warn(
            `syncUserRoleClaim: unrecognized role "${role}" for user ` +
            `${event.params.userId}, skipping.`,
        );
        return;
      }
      await getAuth().setCustomUserClaims(event.params.userId, {role});
    },
);
