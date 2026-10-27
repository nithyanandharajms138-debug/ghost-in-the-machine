
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const terminal = document.getElementById("terminal");

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = input.value.trim();

    if (message === "") {
        return;
    }

    // Display the user's message
    const userParagraph = document.createElement("p");
    userParagraph.textContent = "You: " + message;
    terminal.appendChild(userParagraph);

    input.value = "";

    try {
        // Send the message to our Flask backend
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        // Display the backend's reply
        const ghostParagraph = document.createElement("p");
        ghostParagraph.textContent = "Ghost: " +
            (response.ok ? data.reply : data.error || "Something went wrong.");

        terminal.appendChild(ghostParagraph);

    } catch (error) {
        const errorParagraph = document.createElement("p");
        errorParagraph.textContent =
            "System error: Could not contact the server.";

        terminal.appendChild(errorParagraph);
        console.error(error);
    }
});
