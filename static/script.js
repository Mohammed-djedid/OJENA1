const videoInput = document.getElementById("videoInput");
const uploadBtn = document.getElementById("uploadBtn");
const status = document.getElementById("status");
const dropzone = document.getElementById("dropzone");
const previewCard = document.getElementById("previewCard");
const resultVideo = document.getElementById("resultVideo");
const downloadLink = document.getElementById("downloadLink");

let selectedFile = null;

dropzone.addEventListener("click", () => videoInput.click());
videoInput.addEventListener("change", (e) => {
  selectedFile = e.target.files[0];
  status.innerText = selectedFile ? `Selected: ${selectedFile.name}` : "";
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.style.borderColor = "rgba(255,255,255,0.3)";
});
dropzone.addEventListener("dragleave", (e) => {
  dropzone.style.borderColor = "";
});
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    selectedFile = e.dataTransfer.files[0];
    videoInput.files = e.dataTransfer.files;
    status.innerText = `Selected: ${selectedFile.name}`;
  }
});

uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    status.innerText = "Please select a video file first.";
    return;
  }

  status.innerText = "Uploading...";
  uploadBtn.disabled = true;

  try {
    const form = new FormData();
    form.append("video", selectedFile);

    const res = await fetch("/upload", {
      method: "POST",
      body: form
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");

    status.innerText = "Processing complete! Loading result...";
    previewCard.hidden = false;
    resultVideo.src = data.url + "?t=" + Date.now(); // avoid cache
    downloadLink.href = data.url;
    downloadLink.style.display = "inline-block";
    status.innerText = "Done!";
  } catch (err) {
    console.error(err);
    status.innerText = "Error: " + (err.message || err);
  } finally {
    uploadBtn.disabled = false;
  }
});
