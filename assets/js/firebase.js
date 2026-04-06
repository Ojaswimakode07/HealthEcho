import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
  import { getAuth, RecaptchaVerifier, signInWithPhoneNumber, createUserWithEmailAndPassword, signInWithEmailAndPassword, onAuthStateChanged, signOut, sendEmailVerification, sendPasswordResetEmail, setPersistence, browserLocalPersistence } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
  import { getFirestore, collection, doc, setDoc, getDoc, addDoc, getDocs, query, where, orderBy, Timestamp, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore.js";
  import { getStorage, ref, uploadBytes, getDownloadURL } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-storage.js";

    const defaultFirebaseConfig = {
    apiKey: "AIzaSyA-QR2_Yr6oorg06cE0JoqkRxZiByLSTzI",
    authDomain: "healthecho-7175e.firebaseapp.com",
    projectId: "healthecho-7175e",
    storageBucket: "healthecho-7175e.firebasestorage.app",
    messagingSenderId: "712734876851",
    appId: "1:712734876851:web:0f23d98bfe3fc7cb40fcc6",
    measurementId: "G-SM9JYC10XS"
  };

  const firebaseConfig = window.HEALTHECHO_ENV?.firebase || defaultFirebaseConfig;

  const app = initializeApp(firebaseConfig);
  const auth = getAuth(app);
  const db = getFirestore(app);
  const storage = getStorage(app);

  // â”€â”€ MOBILE FIX: Set session persistence to LOCAL so auth survives mobile browser restarts â”€â”€
  setPersistence(auth, browserLocalPersistence).catch(e => console.warn('Persistence set failed:', e));

  window._FB = { auth, db, storage, collection, doc, setDoc, getDoc, addDoc, getDocs, query, where, orderBy, Timestamp, serverTimestamp, RecaptchaVerifier, signInWithPhoneNumber, createUserWithEmailAndPassword, signInWithEmailAndPassword, onAuthStateChanged, signOut, sendEmailVerification, sendPasswordResetEmail, ref, uploadBytes, getDownloadURL };

  onAuthStateChanged(auth, async (fbUser) => {
    if (fbUser) {
      try {
        const snap = await getDoc(doc(db, 'users', fbUser.uid));
        if (snap.exists()) {
          STATE.user = { id: fbUser.uid, ...snap.data() };
          STATE.firebaseUser = fbUser;
          updateAuthUI();
          loadUserReports();
          loadUserConsultations();
        }
      } catch(e) { console.warn('Firestore fetch error:', e); }
    } else {
      STATE.user = null;
      STATE.firebaseUser = null;
      updateAuthUI();
    }
  });
