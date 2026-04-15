const FIREBASE_VERSION = "11.0.2";
const USERS_KEY = "healthnova_local_users";
const CURRENT_USER_KEY = "healthnova_local_current_user";
const WORKSPACE_KEY = "healthnova_local_workspace";
const FEEDBACK_ENTRIES_KEY = "healthnova_local_feedback_entries";
const FEEDBACK_SUBMITTED_KEY = "healthnova_local_feedback_submitted";
const EMAIL_LINK_KEY = "healthnova_email_link";
const EMAIL_LINK_NAME_KEY = "healthnova_email_link_name";

export const authCapabilities = {
  googleSignIn: true,
  phoneOtp: false,
  mode: "firebase-cdn",
};

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyDXb7A62WcEUAu02HGnQjUfyGU2B7coBpw",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "healthnova-14319.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "healthnova-14319",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "healthnova-14319.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "159480317241",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:159480317241:web:0d6035b6b03eec914194e8",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || "G-6QJWTBSX2Z",
};

let firebaseBundlePromise = null;
let firebaseServicesPromise = null;

function ensureBrowser() {
  if (typeof window === "undefined") {
    throw new Error("This action is only available in the browser.");
  }
}

function readJson(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key, value) {
  window.localStorage.setItem(key, JSON.stringify(value));
}

function normalizeEmail(email = "") {
  return `${email}`.trim().toLowerCase();
}

function mapUser(user) {
  if (!user) return null;
  return {
    uid: user.uid,
    name: user.displayName || user.name || "",
    email: user.email || "",
    photoURL: user.photoURL || "",
  };
}

function loadUsers() {
  return readJson(USERS_KEY, {});
}

function saveUsers(users) {
  writeJson(USERS_KEY, users);
}

function loadCurrentUser() {
  return readJson(CURRENT_USER_KEY, null);
}

function saveCurrentUser(user) {
  writeJson(CURRENT_USER_KEY, user || null);
}

function workspaceStorageKey(uid) {
  return `${WORKSPACE_KEY}:${uid}`;
}

function feedbackSubmittedKey(accountKey) {
  return `${FEEDBACK_SUBMITTED_KEY}:${accountKey}`;
}

function normalizeFeedbackEntries(entries) {
  return (Array.isArray(entries) ? entries : [])
    .map((item) => ({
      id: `${item?.id || ""}`.trim(),
      name: `${item?.name || ""}`.trim(),
      role: `${item?.role || "HealthNova user"}`.trim(),
      quote: `${item?.quote || ""}`.trim(),
      rating: Number(item?.rating || 0),
      badge: `${item?.badge || `${item?.rating || 0}-star feedback`}`.trim(),
      createdAt: item?.createdAt || new Date().toISOString(),
      accountKey: `${item?.accountKey || ""}`.trim().toLowerCase(),
    }))
    .filter((item) => item.id && item.accountKey);
}

function getVisibleFeedbackEntries(entries, limit = 5) {
  return normalizeFeedbackEntries(entries)
    .filter((item) => item.rating >= 4 && item.quote && item.name)
    .sort((left, right) => new Date(right.createdAt || 0).getTime() - new Date(left.createdAt || 0).getTime())
    .slice(0, limit);
}

function getActionCodeSettings() {
  return {
    url: window.location?.origin || "http://localhost:5173",
    handleCodeInApp: true,
  };
}

async function importFromCdn(path) {
  return import(/* @vite-ignore */ `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/${path}`);
}

async function loadFirebaseBundle() {
  ensureBrowser();
  if (!firebaseBundlePromise) {
    firebaseBundlePromise = Promise.all([
      importFromCdn("firebase-app.js"),
      importFromCdn("firebase-auth.js"),
      importFromCdn("firebase-firestore.js"),
    ]).then(([appModule, authModule, firestoreModule]) => ({
      ...appModule,
      ...authModule,
      ...firestoreModule,
    }));
  }
  return firebaseBundlePromise;
}

async function getFirebaseServices() {
  ensureBrowser();
  if (!firebaseServicesPromise) {
    firebaseServicesPromise = (async () => {
      const firebase = await loadFirebaseBundle();
      const app = firebase.getApps().length ? firebase.getApp() : firebase.initializeApp(firebaseConfig);
      const auth = firebase.getAuth(app);
      auth.languageCode = "en";
      const db = firebase.getFirestore(app);
      const googleProvider = new firebase.GoogleAuthProvider();
      googleProvider.setCustomParameters({ prompt: "select_account" });
      return { firebase, app, auth, db, googleProvider };
    })();
  }
  return firebaseServicesPromise;
}

function firebaseErrorMessage(error) {
  const code = error?.code || "";
  const messages = {
    "auth/email-already-in-use": "This email already has a HealthNova account. Use login instead.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/invalid-credential": "The email or password is incorrect.",
    "auth/invalid-login-credentials": "The email or password is incorrect.",
    "auth/missing-password": "Enter your password to continue.",
    "auth/popup-closed-by-user": "Google sign-in was closed before completion.",
    "auth/too-many-requests": "Too many attempts. Try again in a little while.",
    "auth/unauthorized-domain": "Google sign-in is blocked for this domain. Add localhost to Firebase authorized domains.",
    "auth/user-not-found": "No account was found with that email.",
    "auth/user-disabled": "This account has been disabled.",
    "auth/weak-password": "Password should be at least 6 characters.",
    "auth/invalid-action-code": "That email login link is invalid or has already been used.",
    "auth/expired-action-code": "That email login link has expired. Request a fresh login link.",
    "auth/network-request-failed": "Could not reach Firebase. Check your internet connection and try again.",
  };
  return messages[code] || error?.message || "Authentication failed.";
}

function shouldUseLocalFallback(error) {
  const text = `${error?.message || ""} ${error?.code || ""}`.toLowerCase();
  return (
    text.includes("failed to fetch dynamically imported module") ||
    text.includes("importing a module script failed") ||
    text.includes("network") ||
    text.includes("fetch") ||
    text.includes("offline")
  );
}

function clearFirebasePromises() {
  firebaseBundlePromise = null;
  firebaseServicesPromise = null;
}

function localCheckEmailRegistration(email) {
  const normalizedEmail = normalizeEmail(email);
  const users = loadUsers();
  const existing = users[normalizedEmail];
  return {
    exists: Boolean(existing),
    hasPassword: Boolean(existing?.password),
    hasGoogle: false,
    methods: existing?.password ? ["password"] : [],
  };
}

function localSignUpWithEmailPassword(email, password, displayName = "") {
  const normalizedEmail = normalizeEmail(email);
  if (!normalizedEmail) throw new Error("Enter a valid email address.");
  if (`${password}`.length < 6) throw new Error("Password should be at least 6 characters.");
  const users = loadUsers();
  if (users[normalizedEmail]) throw new Error("This email already has a HealthNova account. Use login instead.");
  const user = {
    uid: globalThis.crypto?.randomUUID?.() || `${Date.now()}`,
    name: `${displayName || ""}`.trim(),
    email: normalizedEmail,
    password,
    photoURL: "",
    createdAt: new Date().toISOString(),
  };
  users[normalizedEmail] = user;
  saveUsers(users);
  saveCurrentUser(mapUser(user));
  return { user: mapUser(user) };
}

function localSignInWithEmailPassword(email, password) {
  const normalizedEmail = normalizeEmail(email);
  const users = loadUsers();
  const existing = users[normalizedEmail];
  if (!existing || existing.password !== password) {
    throw new Error("The email or password is incorrect.");
  }
  saveCurrentUser(mapUser(existing));
  return { user: mapUser(existing) };
}

function localLoadUserWorkspace(uid) {
  return readJson(workspaceStorageKey(uid), { reports: [], chatHistory: [], chatTabs: [] });
}

function localSaveUserWorkspace(uid, payload, userProfile = null) {
  if (userProfile?.email) {
    const users = loadUsers();
    const normalizedEmail = normalizeEmail(userProfile.email);
    if (users[normalizedEmail]) {
      users[normalizedEmail] = {
        ...users[normalizedEmail],
        name: userProfile.name || users[normalizedEmail].name,
      };
      saveUsers(users);
    }
  }
  const nextWorkspace = {
    reports: Array.isArray(payload?.reports) ? payload.reports : [],
    chatHistory: Array.isArray(payload?.chatHistory) ? payload.chatHistory : [],
    chatTabs: Array.isArray(payload?.chatTabs) ? payload.chatTabs : [],
    updatedAt: new Date().toISOString(),
  };
  writeJson(workspaceStorageKey(uid), nextWorkspace);
  return nextWorkspace;
}

function localLoadPublicFeedback() {
  const entries = readJson(FEEDBACK_ENTRIES_KEY, []);
  return getVisibleFeedbackEntries(entries, 5);
}

function localSubmitPublicFeedback(payload) {
  const accountKey = `${payload?.accountKey || payload?.user?.uid || payload?.user?.email || "guest"}`.trim().toLowerCase();
  const submittedMarker = feedbackSubmittedKey(accountKey);
  if (window.localStorage.getItem(submittedMarker) === "1") {
    return { alreadySubmitted: true, displayed: false };
  }
  const entry = {
    id: payload?.id || globalThis.crypto?.randomUUID?.() || `${Date.now()}`,
    name: `${payload?.name || "HealthNova user"}`.trim(),
    role: `${payload?.role || "HealthNova user"}`.trim(),
    quote: `${payload?.quote || ""}`.trim(),
    rating: Number(payload?.rating || 0),
    badge: `${payload?.rating || 0}-star feedback`,
    createdAt: payload?.createdAt || new Date().toISOString(),
    accountKey,
  };
  const entries = normalizeFeedbackEntries(readJson(FEEDBACK_ENTRIES_KEY, []));
  const alreadySubmitted = entries.some((item) => item.accountKey === accountKey);
  if (alreadySubmitted) {
    window.localStorage.setItem(submittedMarker, "1");
    return { alreadySubmitted: true, displayed: false };
  }
  const nextEntries = [entry, ...entries];
  writeJson(FEEDBACK_ENTRIES_KEY, nextEntries);
  window.localStorage.setItem(submittedMarker, "1");
  return {
    alreadySubmitted: false,
    displayed: entry.rating >= 4 && Boolean(entry.quote) && Boolean(entry.name),
    entry,
  };
}

async function localHasSubmittedPublicFeedback(accountKey) {
  const normalizedAccountKey = `${accountKey || ""}`.trim().toLowerCase();
  if (!normalizedAccountKey) return false;
  const entries = normalizeFeedbackEntries(readJson(FEEDBACK_ENTRIES_KEY, []));
  return entries.some((item) => item.accountKey === normalizedAccountKey);
}

export async function sendPhoneOtp() {
  throw new Error("Phone OTP is not available in this setup.");
}

export async function verifyPhoneOtp() {
  throw new Error("Phone OTP is not available in this setup.");
}

export function clearPhoneOtpState() {}

export function observeAuthState(callback) {
  ensureBrowser();
  let unsubscribeFirebase = null;
  callback(mapUser(loadCurrentUser()));

  getFirebaseServices()
    .then(({ firebase, auth }) => {
      authCapabilities.mode = "firebase-cdn";
      authCapabilities.googleSignIn = true;
      unsubscribeFirebase = firebase.onAuthStateChanged(auth, (user) => {
        const mapped = mapUser(user);
        saveCurrentUser(mapped);
        callback(mapped);
      });
    })
    .catch(() => {
      authCapabilities.mode = "local";
      authCapabilities.googleSignIn = true;
      callback(mapUser(loadCurrentUser()));
    });

  function handleStorage(event) {
    if (event.key === CURRENT_USER_KEY) {
      callback(mapUser(loadCurrentUser()));
    }
  }

  window.addEventListener("storage", handleStorage);
  return () => {
    window.removeEventListener("storage", handleStorage);
    unsubscribeFirebase?.();
  };
}

export async function signInWithGoogle() {
  ensureBrowser();
  try {
    const { firebase, auth, googleProvider } = await getFirebaseServices();
    const result = await firebase.signInWithPopup(auth, googleProvider);
    const user = mapUser(result.user);
    saveCurrentUser(user);
    return { user };
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      throw new Error("Google sign-in could not start because Firebase did not load. Check internet access and authorized domains.");
    }
    throw new Error(firebaseErrorMessage(error));
  }
}

export async function checkEmailRegistration(email) {
  ensureBrowser();
  try {
    const { firebase, auth } = await getFirebaseServices();
    const methods = await firebase.fetchSignInMethodsForEmail(auth, normalizeEmail(email));
    return {
      exists: methods.length > 0,
      hasPassword: methods.includes("password"),
      hasGoogle: methods.includes("google.com"),
      methods,
    };
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      authCapabilities.mode = "local";
      return localCheckEmailRegistration(email);
    }
    throw new Error(firebaseErrorMessage(error));
  }
}

export async function signUpWithEmailPassword(email, password, displayName = "") {
  ensureBrowser();
  try {
    const { firebase, auth } = await getFirebaseServices();
    const result = await firebase.createUserWithEmailAndPassword(auth, normalizeEmail(email), password);
    if (displayName?.trim()) {
      await firebase.updateProfile(result.user, { displayName: displayName.trim() });
    }
    const user = mapUser(auth.currentUser || result.user);
    saveCurrentUser(user);
    return { user };
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      authCapabilities.mode = "local";
      return localSignUpWithEmailPassword(email, password, displayName);
    }
    throw new Error(firebaseErrorMessage(error));
  }
}

export async function signInWithEmailPassword(email, password) {
  ensureBrowser();
  try {
    const { firebase, auth } = await getFirebaseServices();
    const result = await firebase.signInWithEmailAndPassword(auth, normalizeEmail(email), password);
    const user = mapUser(result.user);
    saveCurrentUser(user);
    return { user };
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      authCapabilities.mode = "local";
      return localSignInWithEmailPassword(email, password);
    }
    throw new Error(firebaseErrorMessage(error));
  }
}

export async function sendForgotPasswordReset(email) {
  ensureBrowser();
  try {
    const { firebase, auth } = await getFirebaseServices();
    await firebase.sendPasswordResetEmail(auth, normalizeEmail(email));
    return { success: true };
  } catch (error) {
    throw new Error(firebaseErrorMessage(error));
  }
}

export async function updateUserPassword(email) {
  return sendForgotPasswordReset(email);
}

export async function sendEmailLoginLink(email, name = "") {
  ensureBrowser();
  try {
    const { firebase, auth } = await getFirebaseServices();
    await firebase.sendSignInLinkToEmail(auth, normalizeEmail(email), getActionCodeSettings());
    window.localStorage.setItem(EMAIL_LINK_KEY, normalizeEmail(email));
    if (`${name || ""}`.trim()) {
      window.localStorage.setItem(EMAIL_LINK_NAME_KEY, `${name}`.trim());
    }
    return { success: true };
  } catch (error) {
    throw new Error(firebaseErrorMessage(error));
  }
}

export async function completeEmailLinkLogin() {
  ensureBrowser();
  try {
    const { firebase, auth } = await getFirebaseServices();
    if (!firebase.isSignInWithEmailLink(auth, window.location.href)) {
      return { completed: false, user: null };
    }
    const storedEmail = window.localStorage.getItem(EMAIL_LINK_KEY);
    const email = storedEmail || window.prompt("Confirm your email address to finish signing in.");
    if (!email) {
      throw new Error("We could not confirm the email address for this login link.");
    }
    const result = await firebase.signInWithEmailLink(auth, email, window.location.href);
    window.localStorage.removeItem(EMAIL_LINK_KEY);
    window.localStorage.removeItem(EMAIL_LINK_NAME_KEY);
    window.history.replaceState({}, document.title, window.location.pathname);
    const user = mapUser(result.user);
    saveCurrentUser(user);
    return { completed: true, user };
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      return { completed: false, user: null };
    }
    throw new Error(firebaseErrorMessage(error));
  }
}

export async function logoutUser() {
  ensureBrowser();
  try {
    const { firebase, auth } = await getFirebaseServices();
    await firebase.signOut(auth);
  } catch (error) {
    if (!shouldUseLocalFallback(error)) {
      throw new Error(firebaseErrorMessage(error));
    }
    clearFirebasePromises();
  } finally {
    saveCurrentUser(null);
  }
}

export async function loadUserWorkspace(uid) {
  ensureBrowser();
  try {
    const { firebase, db } = await getFirebaseServices();
    const docRef = firebase.doc(db, "healthnova_users", uid);
    const snapshot = await firebase.getDoc(docRef);
    const data = snapshot.exists() ? snapshot.data() : {};
    return {
      reports: Array.isArray(data?.reports) ? data.reports : [],
      chatHistory: Array.isArray(data?.chatHistory) ? data.chatHistory : [],
      chatTabs: Array.isArray(data?.chatTabs) ? data.chatTabs : [],
    };
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      authCapabilities.mode = "local";
      return localLoadUserWorkspace(uid);
    }
    throw error;
  }
}

export async function saveUserWorkspace(uid, payload, userProfile = null) {
  ensureBrowser();
  try {
    const { firebase, db } = await getFirebaseServices();
    const docRef = firebase.doc(db, "healthnova_users", uid);
    const current = await firebase.getDoc(docRef);
    const existing = current.exists() ? current.data() : {};
    const nextWorkspace = {
      ...existing,
      uid,
      email: userProfile?.email || existing?.email || "",
      name: userProfile?.name || existing?.name || "",
      reports: Array.isArray(payload?.reports) ? payload.reports : [],
      chatHistory: Array.isArray(payload?.chatHistory) ? payload.chatHistory : [],
      chatTabs: Array.isArray(payload?.chatTabs) ? payload.chatTabs : [],
      updatedAt: firebase.serverTimestamp(),
    };
    await firebase.setDoc(docRef, nextWorkspace, { merge: true });
    return nextWorkspace;
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      authCapabilities.mode = "local";
      return localSaveUserWorkspace(uid, payload, userProfile);
    }
    throw error;
  }
}

export async function loadPublicFeedback() {
  ensureBrowser();
  try {
    const { firebase, db } = await getFirebaseServices();
    const docRef = firebase.doc(db, "healthnova_public", "feedback");
    const snapshot = await firebase.getDoc(docRef);
    const items = snapshot.exists() ? snapshot.data()?.entries : [];
    return getVisibleFeedbackEntries(items, 5);
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      return localLoadPublicFeedback();
    }
    return localLoadPublicFeedback();
  }
}

export async function submitPublicFeedback(payload) {
  ensureBrowser();
  try {
    const { firebase, db } = await getFirebaseServices();
    const accountKey = `${payload?.accountKey || payload?.user?.uid || payload?.user?.email || "guest"}`.trim().toLowerCase();
    const entry = {
      id: payload?.id || globalThis.crypto?.randomUUID?.() || `${Date.now()}`,
      name: `${payload?.name || "HealthNova user"}`.trim(),
      role: `${payload?.role || "HealthNova user"}`.trim(),
      quote: `${payload?.quote || ""}`.trim(),
      rating: Number(payload?.rating || 0),
      badge: `${payload?.rating || 0}-star feedback`,
      createdAt: payload?.createdAt || new Date().toISOString(),
      accountKey,
    };

    const docRef = firebase.doc(db, "healthnova_public", "feedback");
    const snapshot = await firebase.getDoc(docRef);
    const existingEntries = normalizeFeedbackEntries(snapshot.exists() ? snapshot.data()?.entries : []);
    const alreadySubmitted = existingEntries.some((item) => item.accountKey === accountKey);
    if (alreadySubmitted) {
      window.localStorage.setItem(feedbackSubmittedKey(accountKey), "1");
      return { alreadySubmitted: true, displayed: false };
    }
    const nextEntries = [entry, ...existingEntries];
    await firebase.setDoc(docRef, { entries: nextEntries }, { merge: true });
    window.localStorage.setItem(feedbackSubmittedKey(accountKey), "1");
    return {
      alreadySubmitted: false,
      displayed: entry.rating >= 4 && Boolean(entry.quote) && Boolean(entry.name),
      entry,
    };
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      return localSubmitPublicFeedback(payload);
    }
    return localSubmitPublicFeedback(payload);
  }
}

export async function hasSubmittedPublicFeedback(accountKey) {
  ensureBrowser();
  const normalizedAccountKey = `${accountKey || ""}`.trim().toLowerCase();
  if (!normalizedAccountKey || normalizedAccountKey === "guest") {
    return false;
  }

  try {
    const { firebase, db } = await getFirebaseServices();
    const docRef = firebase.doc(db, "healthnova_public", "feedback");
    const snapshot = await firebase.getDoc(docRef);
    const items = normalizeFeedbackEntries(snapshot.exists() ? snapshot.data()?.entries : []);
    const submitted = items.some((item) => item.accountKey === normalizedAccountKey);
    if (submitted) {
      window.localStorage.setItem(feedbackSubmittedKey(normalizedAccountKey), "1");
    }
    return submitted;
  } catch (error) {
    if (shouldUseLocalFallback(error)) {
      clearFirebasePromises();
      return localHasSubmittedPublicFeedback(normalizedAccountKey);
    }
    return localHasSubmittedPublicFeedback(normalizedAccountKey);
  }
}
