// Import Firebase v9 modules (modular approach)
import { initializeApp } from "firebase/app";
import { 
  getAuth, 
  GoogleAuthProvider, 
  signInWithPopup, 
  signOut, 
  onAuthStateChanged 
} from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

const firebaseConfig = {
  apiKey: "AIzaSyDoN-nSGUo_1h87nkOXSXX2vv4IBXBXey0",
  authDomain: "chatify-49.firebaseapp.com",
  projectId: "chatify-49",
  storageBucket: "chatify-49.appspot.com",
  messagingSenderId: "1034185885241",
  appId: "1:1034185885241:web:a46af138b7a40d318defe8",
  measurementId: "G-EHQ2YBVYY9",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize services
const auth = getAuth(app);
const db = getFirestore(app);
const storage = getStorage(app);
const googleProvider = new GoogleAuthProvider();

// Configure Google Provider
googleProvider.setCustomParameters({
  prompt: 'select_account'
});

// Authentication functions
const signInWithGoogle = async () => {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    const user = result.user;
    return { 
      success: true, 
      user: {
        uid: user.uid,
        name: user.displayName,
        email: user.email,
        photoURL: user.photoURL
      }
    };
  } catch (error) {
    console.error("Google Sign-In Error:", error);
    return { 
      success: false, 
      error: error.message 
    };
  }
};

const logout = async () => {
  try {
    await signOut(auth);
    return { success: true };
  } catch (error) {
    console.error("Logout Error:", error);
    return { 
      success: false, 
      error: error.message 
    };
  }
};

// Auth state observer
const onAuthStateChange = (callback) => {
  return onAuthStateChanged(auth, (user) => {
    if (user) {
      callback({
        uid: user.uid,
        name: user.displayName,
        email: user.email,
        photoURL: user.photoURL
      });
    } else {
      callback(null);
    }
  });
};

export { 
  auth, 
  db, 
  storage, 
  googleProvider, 
  signInWithGoogle, 
  logout,
  onAuthStateChange 
};