document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("add-patient-modal-close").addEventListener("click", () => {
    document.getElementById("add-patient-modal-overlay").style.display = "none";
  });

  // Example: trigger from a button
  document.getElementById("add-patient-btn").addEventListener("click", () => {
    document.getElementById("add-patient-modal-overlay").style.display = "flex";
  });

  // Edit modal close
  document.getElementById("edit-patient-modal-close").addEventListener("click", () => {
    document.getElementById("edit-patient-modal-overlay").style.display = "none";
  });

  // Handle add patient form submission
  document.querySelector(".add-patient-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData();

    // Input'ları placeholder ile bul
    formData.append("name", document.getElementById('patient-name').value);
    formData.append("surname", document.getElementById('patient-surname').value);
    formData.append("height", document.getElementById('patient-height').value);
    formData.append("weight", document.getElementById('patient-weight').value);
    formData.append("age", document.getElementById('patient-age').value);
    formData.append("gender", document.querySelector('input[name="gender"]:checked').value);

    try {
      const response = await fetch("/create-patient", {
        method: "POST",
        body: formData
      });
      
      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        document.getElementById("add-patient-modal-overlay").style.display = "none";
        // Sayfayı yenile
        location.reload();
      } else {
        alert(result.error || "Hasta eklenemedi.");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("Bir hata oluştu.");
    }
  });

  // Handle edit patient form submission
  document.querySelector(".edit-patient-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const form = e.target;
    const patientId = document.getElementById("edit-patient-id").value;
    const formData = new FormData();
    
    formData.append("name", document.getElementById("edit-patient-name").value);
    formData.append("surname", document.getElementById("edit-patient-surname").value);
    formData.append("height", document.getElementById("edit-patient-height").value);
    formData.append("weight", document.getElementById("edit-patient-weight").value);
    formData.append("age", document.getElementById("edit-patient-age").value);
    formData.append("gender", form.querySelector('input[name="edit-gender"]:checked').value);

    try {
      const response = await fetch(`/edit-patient/${patientId}`, {
        method: "PUT",
        body: formData
      });
      
      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        document.getElementById("edit-patient-modal-overlay").style.display = "none";
        location.reload();
      } else {
        alert(result.error || "Hasta güncellenemedi.");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("Bir hata oluştu.");
    }
  });

  // Function to open edit modal and populate with patient data
  async function editPatient(patientId, name, surname) {
    try {
      // Hasta bilgilerini backend'den al
      const response = await fetch(`/patient-info/${patientId}`);
      if (!response.ok) {
        alert("Hasta bilgileri alınamadı.");
        return;
      }
      
      const patientData = await response.json();
      
      // Form alanlarını doldur
      document.getElementById("edit-patient-id").value = patientId;
      document.getElementById("edit-patient-name").value = patientData.name;
      document.getElementById("edit-patient-surname").value = patientData.surname;
      document.getElementById("edit-patient-height").value = patientData.height;
      document.getElementById("edit-patient-weight").value = patientData.weight;
      document.getElementById("edit-patient-age").value = patientData.age;
      
      // Gender radio button'ını seç
      const genderRadio = document.querySelector(input[name="edit-gender"][value="${patientData.gender}"]);
      if (genderRadio) {
        genderRadio.checked = true;
      }
      
      // Modal'ı göster
      document.getElementById("edit-patient-modal-overlay").style.display = "flex";
    } catch (error) {
      console.error("Error:", error);
      alert("Bir hata oluştu.");
    }
  }

  // Function to delete patient
  async function deletePatient(patientId, patientName) {
    if (!confirm(`${patientName}` + " adlı hastayı silmek istediğinizden emin misiniz?")) {
      return;
    }
    
    try {
      const response = await fetch(`/delete-patient/${patientId}`, {
        method: "DELETE"
      });
      
      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        location.reload();
      } else {
        alert(result.error || "Hasta silinemedi.");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("Bir hata oluştu.");
    }
  }
});