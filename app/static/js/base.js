async function getDoctorInfo() {
    try {
        const response = await fetch("http://127.0.0.1:8000/doctor-info", {
            method: "GET",
            credentials: "include"  // ✅ Send cookies (session_token)
        });

        if (!response.ok) {
            throw new Error("Failed to fetch doctor info");
        }

        const data = await response.json();
        console.log("Doctor info:", data.data);

        // Example: Update HTML dynamically
        document.getElementById("patient-count").textContent = data.data.patient_count;
        document.getElementById("doctor-name").textContent = data.data.name + " " + data.data.surname;
        document.getElementById("doctor-institution").textContent = data.data.institution;
        document.getElementById("doctor-title").textContent = data.data.title;
        document.getElementById("doctor-created-on").textContent = data.data.created_on;

    } catch (error) {
        console.error("Error:", error);
        alert("Could not fetch doctor info");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Doctor Info Modal Elements
    const doctorCircle = document.getElementById('doctor-circle');
    const doctorInfoModal = document.getElementById('doctor-info-modal');
    const closeDoctorModal = document.getElementById('close-doctor-modal');
    const changePasswordButton = document.getElementById('change-password-btn'); 
    const logoutButton = document.getElementById('logout-button');
    const deleteAccountButton = document.getElementById('delete-account-btn');
    // Change Password Modal Elements
    const changePasswordModal = document.getElementById('change-password-modal'); 
    const closePasswordModal = document.getElementById('close-password-modal');
    const changePasswordForm = document.getElementById('change-password-form'); 
    // Delete Account Modal Elements (New)
    const deleteAccountModal = document.getElementById('delete-account-modal');
    const closeDeleteAccountModal = document.getElementById('close-delete-account-modal');
    const deleteAccountForm = document.getElementById('delete-account-form');
    const deleteAccountMessage = document.getElementById('delete-account-message');

    // Doctor Info Modal Logic
    doctorCircle.addEventListener('click', async (event) => {
        event.preventDefault();
        await getDoctorInfo();

        doctorInfoModal.style.display = 'flex';
    });

    deleteAccountButton.addEventListener('click', () => {
    if (doctorInfoModal) {
        doctorInfoModal.style.display = 'none';
    }
    if (deleteAccountModal) {
        deleteAccountModal.style.display = 'flex';
        deleteAccountMessage.textContent = ''; // Clear previous messages
        document.getElementById('delete-current-password').value = ''; // Clear password field
    }
});

    closeDoctorModal.addEventListener('click', () => {
        doctorInfoModal.style.display = 'none';
    });

    closeDeleteAccountModal.addEventListener('click', () => {
    deleteAccountModal.style.display = 'none';
});

    // Open Change Password Modal from Doctor Info Modal
    changePasswordButton.addEventListener('click', () => {
        if (doctorInfoModal) { 
            doctorInfoModal.style.display = 'none'; // Doktor profil modalını gizle
        }
        if (changePasswordModal) { 
            changePasswordModal.style.display = 'flex'; // Şifre değiştirme modalını göster
        }
    });
    logoutButton.addEventListener('click', () => {
        console.log("Pressed!");
        window.location.href = `http://127.0.0.1:8000/log-out`;
    });

    // Close Change Password Modal
    closePasswordModal.addEventListener('click', () => {
        changePasswordModal.style.display = 'none';
    });

    changePasswordForm.addEventListener('submit', async (event) => {
    event.preventDefault(); 
    
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const passwordMessage = document.getElementById('password-message'); 

 
    if (newPassword !== confirmPassword) {
        passwordMessage.textContent = 'New passwords do not match!';
        passwordMessage.style.color = 'red';
        return; 
    }

    if (newPassword.length < 6) {
        passwordMessage.textContent = 'New password must be at least 6 characters long!';
        passwordMessage.style.color = 'red';
        return; 
    }

    try {
        
        const formData = new FormData();
        formData.append('current_password', currentPassword);
        formData.append('new_password', newPassword);

        
        const response = await fetch('http://127.0.0.1:8000/change-password', {
            method: 'POST',
            credentials: 'include', 
            body: formData 
        });

        const data = await response.json(); 

        if (response.ok) {
            
            passwordMessage.textContent = 'Password changed successfully!';
            passwordMessage.style.color = 'green';
            changePasswordForm.reset();

            
            setTimeout(() => {
                changePasswordModal.style.display = 'none';
                passwordMessage.textContent = '';
            }, 2000);
        } else {
            passwordMessage.textContent = data.error || 'Password change failed!';
            passwordMessage.style.color = 'red';
        }
    } catch (error) {
        console.error('Password change error:', error);
        passwordMessage.textContent = 'An error occurred. Please try again.';
        passwordMessage.style.color = 'red';
    }
    });

    deleteAccountForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const currentPassword = document.getElementById('delete-current-password').value;

    const formData = new FormData();
    formData.append('current_password', currentPassword);

    try {
        const response = await fetch('http://127.0.0.1:8000/delete-account', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            deleteAccountMessage.textContent = result.message;
            deleteAccountMessage.style.color = 'green';
            // Redirect to sign-in page after successful deletion
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
        } else {
            deleteAccountMessage.textContent = result.error || 'Account deletion failed!';
            deleteAccountMessage.style.color = 'red';
        }
    } catch (error) {
        console.error('Account deletion error:', error);
        deleteAccountMessage.textContent = 'An error occurred. Please try again.';
        deleteAccountMessage.style.color = 'red';
    }
    });
});