import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, sendPasswordResetEmail} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getFirestore, doc, getDoc } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyDY16dhYdK_mIyCrLK3h-bwlxycP4gi6Fk",
  authDomain: "cerebrumal.firebaseapp.com",
  projectId: "cerebrumal",
  storageBucket: "cerebrumal.appspot.com",
  messagingSenderId: "232446464501",
  appId: "1:232446464501:web:b8532820cf98511c6690bc"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

async function signInDoctor(email,password){
    try{
        // Sign in with firebase Auth
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;

        // Check if doctor record exists
        const doctorDoc = await getDoc(doc(db, "doctor", user.uid));
        if (!doctorDoc.exists()){
            await auth.signOut();
            alert("Access denied: You are not registered as a doctor." + user.uid);
            return;
        }

        // Get ID token (JWT) to send to backend
        const idToken = await user.getIdToken();

        // Call backend API with token
        window.location.href = `http://127.0.0.1:8000/doctor-area?token=${idToken}`;
    }catch(error){
        console.error("Sign-in failed:", error);
        alert("Access denied: You are not registered as a doctor.");
    }
}

async function sendPasswordReset(email) {
    try {
        await sendPasswordResetEmail(auth, email);
        alert("Password reset email has been sent! Please check your inbox.");
    } catch (error) {
        console.error("Password reset error:", error);

        if (error.code === 'auth/user-not-found') {
            alert("No user found with this email address. Please enter a valid email.");
        } else if (error.code === 'auth/invalid-email') {
            alert("Invalid email address. Please enter a valid format.");
        } else {
            alert("Password reset failed.");
        }
    }
}



document.addEventListener("DOMContentLoaded", () => {
    /* --------------! About Us Modal !---------------- */
    const aboutLink = document.getElementById('about-link');
    const aboutModal = document.getElementById('about-modal');
    const closeModal = document.getElementById('close-modal');

    aboutLink.addEventListener('click', () => {
        aboutModal.style.display = 'flex';
    });

    closeModal.addEventListener('click', () => {
        aboutModal.style.display = 'none';
    });

    /* --------------! Sign In Functionality  !---------------- */

    const loginForm = document.getElementById('login-form');
    const forgotPasswordLink = document.getElementById('forgot-password-link'); 

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        await signInDoctor(email, password);
    });
    
    if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener('click', async (event) => {
        event.preventDefault();
        const email = document.getElementById('email').value; // Get the email from the input field
        if (email) {
            await sendPasswordReset(email);
        } else {
            alert("Please enter your email address to reset your password.");
        }
    });
    }

});