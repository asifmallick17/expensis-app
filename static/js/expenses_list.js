// Fetch expenses from localStorage (added from expense.html form)
let expenses = JSON.parse(localStorage.getItem("expenses")) || [];

let tableBody = document.querySelector("#expenseTable tbody");
let totalExpense = 0;

expenses.forEach((exp) => {
  let row = document.createElement("tr");
  row.innerHTML = `
    <td>${exp.date}</td>
    <td>${exp.title}</td>
    <td>${exp.category}</td>
    <td>₹${exp.amount}</td>
    <td>${exp.notes}</td>
  `;
  tableBody.appendChild(row);

  totalExpense += parseFloat(exp.amount);
});

document.getElementById("totalExpense").textContent = `₹${totalExpense}`;
