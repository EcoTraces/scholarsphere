"use strict";

// One-time (safe to re-run) backfill: sets every existing user's Firebase
// Auth custom claim to match their `users/{uid}.role` Firestore field.
// Needed because `syncUserRoleClaim` (see functions/index.js) only fires
// on future writes to a user document - accounts whose role was already
// set before that trigger was deployed (via createManagedUser before this
// script existed, or a direct Firestore edit) still have a missing or
// stale custom claim until either this runs once, or their document is
// written to again.

const {applicationDefault, initializeApp} = require("firebase-admin/app");
const {getAuth} = require("firebase-admin/auth");
const {getFirestore} = require("firebase-admin/firestore");

initializeApp({
  credential: applicationDefault(),
  projectId: process.env.GCLOUD_PROJECT || "scholarsphere-d44f5",
});

const allRoles = new Set([
  "applicant",
  "opportunityProvider",
  "verificationOfficer",
  "moderator",
  "supportOfficer",
  "administrator",
  "securityAdministrator",
  "superAdministrator",
]);

async function main() {
  const snapshot = await getFirestore().collection("users").get();
  let updated = 0;
  let skipped = 0;
  for (const doc of snapshot.docs) {
    const role = doc.data().role;
    if (!allRoles.has(role)) {
      console.warn(`Skipping ${doc.id}: unrecognized role "${role}".`);
      skipped++;
      continue;
    }
    await getAuth().setCustomUserClaims(doc.id, {role});
    console.log(`${doc.id}: role=${role}`);
    updated++;
  }
  console.log(`Done. ${updated} account(s) updated, ${skipped} skipped.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
