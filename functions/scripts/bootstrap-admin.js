"use strict";

const {applicationDefault, initializeApp} = require("firebase-admin/app");
const {getAuth} = require("firebase-admin/auth");
const {FieldValue, getFirestore} = require("firebase-admin/firestore");

initializeApp({
  credential: applicationDefault(),
  projectId: process.env.GCLOUD_PROJECT || "scholarsphere-d44f5",
});

async function main() {
  const email = process.env.BOOTSTRAP_ADMIN_EMAIL;
  if (!email) {
    throw new Error("Set BOOTSTRAP_ADMIN_EMAIL before running this script.");
  }
  const normalizedEmail = email.trim().toLowerCase();
  let user;
  try {
    user = await getAuth().getUserByEmail(normalizedEmail);
  } catch (error) {
    if (error.code !== "auth/user-not-found") throw error;
    const password = process.env.BOOTSTRAP_ADMIN_PASSWORD;
    if (!password || password.length < 12) {
      throw new Error(
          "Set BOOTSTRAP_ADMIN_PASSWORD to at least 12 characters.",
      );
    }
    user = await getAuth().createUser({
      email: normalizedEmail,
      password,
      displayName: "ScholarSphere Administrator",
      emailVerified: true,
    });
  }
  await getAuth().setCustomUserClaims(user.uid, {role: "superAdministrator"});
  await getFirestore().collection("users").doc(user.uid).set(
      {
        uid: user.uid,
        fullName: user.displayName || "ScholarSphere Administrator",
        email: user.email,
        role: "superAdministrator",
        status: "active",
        emailVerified: user.emailVerified,
        twoFactorEnabled: false,
        marketingEmailsEnabled: false,
        deadlineNotificationsEnabled: true,
        updatedAt: FieldValue.serverTimestamp(),
      },
      {merge: true},
  );
  console.log(`Bootstrapped administrator ${user.uid}.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
