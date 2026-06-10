// Boutique VertiFarm — front minimal (vanilla JS, aucun framework).
const cart = {};

async function loadProducts() {
  const el = document.getElementById("products");
  try {
    const res = await fetch("/api/products");
    const products = await res.json();
    el.innerHTML = "";
    products.forEach((p) => {
      const score = (p.green_score === null || p.green_score === undefined)
        ? "" : `<span class="badge">Green Score ${p.green_score}</span>`;
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h3>${p.name}${score}</h3>
        <p>Ferme : ${p.farm_id}</p>
        <p class="price">${p.price_eur.toFixed(2)} € / ${p.unit}</p>
        <button data-id="${p.id}" data-name="${p.name}">Ajouter</button>`;
      card.querySelector("button").addEventListener("click", () => addToCart(p));
      el.appendChild(card);
    });
  } catch (e) {
    el.textContent = "Impossible de charger le catalogue.";
  }
}

function addToCart(p) {
  cart[p.id] = cart[p.id] || { name: p.name, quantity: 0 };
  cart[p.id].quantity += 1;
  renderCart();
}

function renderCart() {
  const ul = document.getElementById("cart");
  ul.innerHTML = "";
  Object.entries(cart).forEach(([id, item]) => {
    const li = document.createElement("li");
    li.textContent = `${item.name} × ${item.quantity}`;
    ul.appendChild(li);
  });
}

async function checkout() {
  const customer = document.getElementById("customer").value.trim();
  const msg = document.getElementById("message");
  const lines = Object.entries(cart).map(([id, item]) => ({ product_id: id, quantity: item.quantity }));
  if (!customer || lines.length === 0) {
    msg.textContent = "Indiquez votre nom et ajoutez au moins un produit.";
    return;
  }
  const res = await fetch("/api/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ customer, lines }),
  });
  if (res.ok) {
    const order = await res.json();
    msg.textContent = `Merci ! Commande ${order.id.slice(0, 8)} enregistrée pour demain.`;
    Object.keys(cart).forEach((k) => delete cart[k]);
    renderCart();
  } else {
    msg.textContent = "Erreur lors de la commande.";
  }
}

document.getElementById("checkout").addEventListener("click", checkout);
loadProducts();
