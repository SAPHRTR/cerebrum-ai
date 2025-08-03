const STATIC_URL_BASE = "{{ url_for('static', path='') }}"

document.addEventListener("DOMContentLoaded", () => {
  // Close modal on clicking the X button
  document.getElementById('result-modal-close').addEventListener('click', () => {
    document.getElementById('result-modal-overlay').style.display = 'none';
  });

  document.querySelectorAll('.patient-result').forEach(link => {
    link.addEventListener('click', async (event) => {
        const resultId = event.target.getAttribute('data-id');

        try {
            // Fetch result info from backend
            const response = await fetch(`/result/${resultId}`);
            if (!response.ok) {
              throw new Error("Failed to fetch result info.");
            }

            const data = await response.json();
            console.log(data.data);

            // Populate modal with fetched data
            document.getElementById('result-title').textContent = `${data.data.title}`;
            document.getElementById('patient-name').textContent = `${data.data.patient_name}`;
            document.getElementById('tumor-type-label').textContent = `${data.data.tumor_type}`;
            document.getElementById('tumor-rate-label').textContent = `${data.data.pred_rate}`;
            document.getElementById('tumor-description').textContent = `${data.data.description}`;
            const myPath = `${data.data.image_path}`;
            const fullImageUrl = `${STATIC_BASE_URL}${myPath}`;           
            document.getElementById('mri-image').src = fullImageUrl;
            document.getElementById('scanned-on').textContent = `Scanned On: ${data.data.scanned_on}`;
            // TODO: HANDLE IMAGE DATA!

            // Show modal
            document.getElementById('result-modal-overlay').style.display = 'flex';

          } catch (err) {
            console.error(err);
            alert("Could not load result details.");
          }
        });
    });
});