// Get elements
const openPopupBtn = document.getElementById('ainaFloatingButton');
const popupModal = document.getElementById('popupModal');
const closeModal = document.querySelector('.close');
const popupForm = document.getElementById('popupForm');
const textInput = document.getElementById('textInput');
const modalText = document.getElementById('modalText');
const frame = document.getElementById('ainaFrame');

// Function to open the modal
openPopupBtn.addEventListener('click', async (event) => {
    const selectedText = frame.getSelection().toString();
    console.log(selectedText);
    if (!selectedText) {
        alert('Please select some text before submitting.');
        return;
    }

    const queryString = window.location.search;
    console.log(queryString);
    const urlParams = new URLSearchParams(queryString);
    const pageUrl = urlParams.get('url');
    const response = await fetch('/lookupTranslation?' + new URLSearchParams({
        text: selectedText,
        url: pageUrl,
    }), {
        method: 'GET',
    });
    if (!response.ok) {
        alert('Failed to lookup translation.');
        return;
    }

    const data = await response.json();
    if (data.originalText) {
        modalText.innerText = '"' + data.originalText + '"';
    } else {
        modalText.innerText = 'No translation found for "' + selectedText + '"';
    }

    popupModal.style.display = 'flex';
});

// Function to close the modal
closeModal.addEventListener('click', () => {
    popupModal.style.display = 'none';
});

// Close modal if clicked outside of content
window.addEventListener('click', (event) => {
    if (event.target === popupModal) {
        popupModal.style.display = 'none';
    }
});

// Handle form submission
popupForm.addEventListener('submit', async (event) => {
    event.preventDefault(); // Prevent form from reloading the page

    const enteredText = textInput.value;
    try {
        // Send POST request
        const response = await fetch('/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: enteredText }),
        });

        if (response.ok) {
            alert('Text submitted successfully!');
        } else {
            alert('Failed to submit text.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred.');
    }

    // Close the modal and reset the form
    popupModal.style.display = 'none';
    popupForm.reset();
});
