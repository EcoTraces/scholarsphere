# Firebase Authentication Deployment

ScholarSphere uses Firebase Authentication for credentials and Firestore
`users/{uid}` documents for account roles, status, and user preferences.
Managed accounts are created only by callable Cloud Functions using the
Firebase Admin SDK.

## Firebase console

In project `scholarsphere-d44f5`:

1. Enable Email/Password and Google in Authentication > Sign-in method.
2. Create the Firestore database in production mode.
3. Add production web domains under Authentication > Authorized domains.
4. Add Android SHA-1 and SHA-256 fingerprints before enabling Google sign-in.
5. Replace the example Android application ID and Apple bundle ID before the
   production release, then run `flutterfire configure` again.

## Install and deploy

```powershell
cd functions
npm install
cd ..
firebase deploy --only firestore,functions
```

The deploy publishes:

- Firestore access rules and indexes.
- `createManagedUser`, which creates Auth users, custom role claims, and
  Firestore account documents.
- `suspendUser`, which disables Auth users and revokes their refresh tokens.

## Bootstrap the first administrator

Use Application Default Credentials or a securely stored service account. Do
not put the password or service-account JSON in the repository.

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\secure\service-account.json"
$env:BOOTSTRAP_ADMIN_EMAIL = "administrator@example.com"
$env:BOOTSTRAP_ADMIN_PASSWORD = "replace-with-a-strong-temporary-password"
cd functions
npm run bootstrap-admin
```

If the Auth user already exists, the script keeps it and assigns the
`superAdministrator` custom claim. The user must sign out and back in after a
claim change so Firebase refreshes the ID token.

## Account behavior

- Applicants self-register and receive a Firebase verification email.
- An applicant remains `pendingVerification` until Firebase confirms the email.
- Administrators create provider and operational accounts.
- Only a super administrator can create privileged administrator accounts.
- Firestore rules prevent clients from assigning roles or suspending accounts.

## Persistence boundary

This implementation persists authentication and account records in Firebase.
Other ScholarSphere repositories still named `Demo...Repository` remain
in-memory and must be migrated module by module. Do not dual-write Firebase
account records to PostgreSQL. If PostgreSQL is introduced for business data,
the backend should verify Firebase ID tokens and use the Firebase UID as the
stable user identifier.
