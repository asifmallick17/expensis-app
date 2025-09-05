let lineChart, barChart, pieChart, doughnutChart;

document.addEventListener("DOMContentLoaded", function () {
  const timePeriodSelect = document.getElementById("time-period");
  timePeriodSelect.addEventListener("change", fetchAndRenderCharts);

  // Initial render with 'day' data
  fetchAndRenderCharts();
});

async function fetchAndRenderCharts() {
  const timePeriod = document.getElementById("time-period").value;

  try {
    const response = await fetch(
      `/api/analysis_data?time_period=${timePeriod}`
    );
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    const data = await response.json();
    updateCharts(data);
  } catch (error) {
    console.error("Error fetching data:", error);
    // You can handle the error more gracefully here, e.g., show an error message on the page
  }
}

function updateCharts(data) {
  const { line_chart, category_charts } = data;

  // Destroy existing charts to prevent stacking
  if (lineChart) lineChart.destroy();
  if (barChart) barChart.destroy();
  if (pieChart) pieChart.destroy();
  if (doughnutChart) doughnutChart.destroy();

  // Line Chart
  lineChart = new Chart(document.getElementById("lineChart"), {
    type: "line",
    data: {
      labels: line_chart.labels,
      datasets: [
        {
          label: "Total Expenses ($)",
          data: line_chart.amounts,
          borderColor: "#64ffda",
          backgroundColor: "rgba(100, 255, 218, 0.15)",
          fill: true,
          tension: 0.25,
          borderWidth: 2,
          pointBackgroundColor: "#64ffda",
          pointRadius: 4,
        },
      ],
    },
    options: {
      plugins: {
        legend: {
          labels: {
            color: "#64ffda",
            font: { size: 14 },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: "#64ffda" },
          grid: { color: "rgba(100,255,218,0.1)" },
        },
        y: {
          ticks: { color: "#64ffda" },
          grid: { color: "rgba(100,255,218,0.1)" },
        },
      },
    },
  });

  // Bar Chart
  barChart = new Chart(document.getElementById("barChart"), {
    type: "bar",
    data: {
      labels: category_charts.labels,
      datasets: [
        {
          label: "Category-wise Expenses ($)",
          data: category_charts.amounts,
          backgroundColor: [
            "#64ffda",
            "#00bcd4",
            "#0097a7",
            "#26c6da",
            "#4dd0e1",
          ],
        },
      ],
    },
  });

  // Pie Chart
  pieChart = new Chart(document.getElementById("pieChart"), {
    type: "pie",
    data: {
      labels: category_charts.labels,
      datasets: [
        {
          data: category_charts.amounts,
          backgroundColor: ["#64ffda", "#00acc1", "#00838f", "#4dd0e1"],
        },
      ],
    },
  });

  // Doughnut Chart
  doughnutChart = new Chart(document.getElementById("doughnutChart"), {
    type: "doughnut",
    data: {
      labels: category_charts.labels,
      datasets: [
        {
          data: category_charts.amounts,
          backgroundColor: ["#64ffda", "#00bcd4", "#00838f", "#4dd0e1"],
        },
      ],
    },
  });
}
