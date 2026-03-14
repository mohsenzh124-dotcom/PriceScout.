(function () {
    "use strict";

    const queryInput = document.getElementById("queryInput");
    const compareButton = document.getElementById("compareButton");
    const statusMessage = document.getElementById("statusMessage");
    const resultsArea = document.getElementById("resultsArea");

    /**
     * Set a status message with optional style variant.
     * @param {string} message
     * @param {"error"|"success"|""} variant
     */
    function setStatus(message, variant) {
        statusMessage.textContent = message;
        statusMessage.className = "status";
        if (variant === "error") {
            statusMessage.classList.add("status--error");
        }
        if (variant === "success") {
            statusMessage.classList.add("status--success");
        }
    }

    /**
     * Remove all previously rendered results.
     */
    function clearResults() {
        while (resultsArea.firstChild) {
            resultsArea.removeChild(resultsArea.firstChild);
        }
    }

    /**
     * Build and append a single offer card.
     * @param {object} offer
     * @param {boolean} isBestOffer
     */
    function renderOfferCard(offer, isBestOffer) {
        const article = document.createElement("article");
        article.className = "result-card";
        if (isBestOffer) {
            article.classList.add("result-card--best");
        }

        const title = document.createElement("h3");
        title.className = "result-card__title";
        title.textContent = offer.product_name || "Unnamed product";

        if (isBestOffer) {
            const badge = document.createElement("span");
            badge.className = "result-card__badge";
            badge.textContent = "Best offer";
            title.appendChild(badge);
        }

        const meta = document.createElement("p");
        meta.className = "result-card__meta";
        const amount = Number(offer.price_amount);
        const safeAmount = Number.isFinite(amount) ? amount.toFixed(2) : String(offer.price_amount);
        meta.textContent = `${offer.store_name} · ${safeAmount} ${offer.currency}`;

        article.appendChild(title);
        article.appendChild(meta);

        if (offer.product_url) {
            const link = document.createElement("a");
            link.className = "result-card__link";
            link.href = offer.product_url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "View product";
            article.appendChild(link);
        }

        resultsArea.appendChild(article);
    }

    /**
     * Render comparison payload from API.
     * @param {object} payload
     */
    function renderPayload(payload) {
        clearResults();

        if (!payload || !Array.isArray(payload.offers) || payload.offers.length === 0) {
            setStatus("No offers found for this query.", "error");
            return;
        }

        const bestUrl = payload.best_offer && payload.best_offer.product_url ? payload.best_offer.product_url : null;
        payload.offers.forEach(function (offer) {
            const isBestOffer = Boolean(bestUrl && offer.product_url === bestUrl);
            renderOfferCard(offer, isBestOffer);
        });

        setStatus(`Found ${payload.total_offers} offers for "${payload.query}".`, "success");
    }

    /**
     * Perform API request and refresh UI state.
     */
    async function comparePrices() {
        const query = queryInput.value.trim();
        clearResults();

        if (!query) {
            setStatus("Please enter a search query.", "error");
            queryInput.focus();
            return;
        }

        compareButton.disabled = true;
        setStatus("Loading offers...", "");

        try {
            const response = await fetch(`/api/compare?q=${encodeURIComponent(query)}`, {
                method: "GET",
                headers: {
                    Accept: "application/json"
                }
            });

            let payload = null;
            try {
                payload = await response.json();
            } catch (_error) {
                payload = null;
            }

            if (!response.ok) {
                const errorMessage = payload && payload.error ? payload.error : "Failed to fetch comparison results.";
                setStatus(errorMessage, "error");
                return;
            }

            renderPayload(payload);
        } catch (_error) {
            setStatus("Network error while fetching comparison results.", "error");
        } finally {
            compareButton.disabled = false;
        }
    }

    compareButton.addEventListener("click", comparePrices);
    queryInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            comparePrices();
        }
    });
})();
