
const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const terminal = document.getElementById("terminal");

// Display text one character at a time.
function typeText(element, text, speed = 25) {
    let index = 0;

    function typeNextCharacter() {
        if (index < text.length) {
            element.textContent += text[index];
            index++;

            terminal.scrollTop = terminal.scrollHeight;
            setTimeout(typeNextCharacter, speed);
        }
    }

    typeNextCharacter();
}

form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const message = input.value.trim();

    if (message === "") {
        return;
    }

    // Display the user's message.
    const userParagraph = document.createElement("p");
    userParagraph.textContent = "You: " + message;
    terminal.appendChild(userParagraph);

    input.value = "";

    try {
        // Send the message to our Flask backend.
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        // Create the ghost's reply.
        const ghostParagraph = document.createElement("p");
        terminal.appendChild(ghostParagraph);

        const reply = response.ok
            ? data.reply
            : data.reply || data.error || "Something went wrong.";

        ghostParagraph.textContent = "Ghost: ";
        typeText(ghostParagraph, reply);

    } catch (error) {
        const errorParagraph = document.createElement("p");
        errorParagraph.textContent =
            "System error: Could not contact the server.";

        terminal.appendChild(errorParagraph);
        console.error(error);
    }
});

    
window.addEventListener("load", async function () {
    input.disabled = true;

    const bootMessages = [
        "[ SYSTEM BOOTING... ]",
        "[ A PRESENCE HAS BEEN DETECTED. ]"
    ];

    for (const message of bootMessages) {
        const paragraph = document.createElement("p");
        terminal.appendChild(paragraph);

        // Type each boot message letter by letter.
        typeText(paragraph, message, 35);

        // Wait until typing finishes, then pause.
        await new Promise(resolve =>
            setTimeout(resolve, message.length * 35 + 900)
        );
    }

    const welcomeParagraph = document.createElement("p");
    terminal.appendChild(welcomeParagraph);

    const welcomeMessage =
        "Ghost: ...Is someone there? Welcome to my little corner of the machine.";

    typeText(welcomeParagraph, welcomeMessage, 35);

    await new Promise(resolve =>
        setTimeout(resolve, welcomeMessage.length * 35 + 100)
    );

    input.disabled = false;
    input.focus();
});
