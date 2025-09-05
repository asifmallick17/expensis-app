document.getElementById("expenseForm").addEventListener("submit", function (e) {
  e.preventDefault();

  let title = document.getElementById("title").value;
  let amount = document.getElementById("amount").value;
  let date = document.getElementById("date").value;
  let category = document.getElementById("category").value;
  let notes = document.getElementById("notes").value;

  let table = document
    .getElementById("expenseTable")
    .getElementsByTagName("tbody")[0];
  let newRow = table.insertRow();

  newRow.innerHTML = `
        <td>${date}</td>
        <td>${title}</td>
        <td>${category}</td>
        <td>₹${amount}</td>
        <td>${notes}</td>
    `;

  // Reset form after submit
  document.getElementById("expenseForm").reset();
  document.getElementById("category").reset();
});
