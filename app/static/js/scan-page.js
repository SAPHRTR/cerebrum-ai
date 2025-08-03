const fileUploadInput = document.getElementById("mri-upload");
const fileUploadLabel = document.querySelector(".file-label");
fileUploadInput.addEventListener("change", function() {
    if (this.files.length > 0) {
        fileUploadLabel.textContent = this.files[0].name;
    } else {
        fileUploadLabel.textContent = "Upload your file";
    }
});

document.getElementById("mri-form").addEventListener("submit", async function(e) {
    e.preventDefault();

    const fileInput = document.getElementById("mri-upload");
    const patientIdInput = document.getElementById("patient-id");
    const resultDiv = document.getElementById("upload-result");
    resultDiv.textContent = "Analyzing...";

    if (fileInput.files.length === 0) {
        resultDiv.textContent = "Please select a file first.";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("patient_id", patientIdInput.value);

    try {
        const response = await fetch("/scan-mri", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        resultDiv.textContent = data.message || "Analysis complete.";
    } catch (error) {
        resultDiv.textContent = "An error occurred while uploading.";
        console.error(error);
    }finally {
        document.getElementById("mri-form").reset();
        fileUploadLabel.textContent = "Upload your file"; 
    }

});