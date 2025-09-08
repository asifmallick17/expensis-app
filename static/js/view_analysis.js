let lineChart, barChart, pieChart;

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
    alert("Failed to load expense data. Please try again.");
  }
}

function updateCharts(data) {
  const { line_chart, category_charts } = data;

  // Destroy existing charts to prevent stacking
  if (lineChart) lineChart.destroy();
  if (barChart) barChart.destroy();
  if (pieChart) pieChart.destroy();

  // Handle empty data
  const lineLabels = line_chart.labels.length ? line_chart.labels : ["No Data"];
  const lineData = line_chart.amounts.length ? line_chart.amounts : [0];
  const categoryLabels = category_charts.labels.length
    ? category_charts.labels
    : ["No Data"];
  const categoryData = category_charts.amounts.length
    ? category_charts.amounts
    : [0];

  // Line Chart
  lineChart = new Chart(document.getElementById("lineChart"), {
    type: "line",
    data: {
      labels: lineLabels,
      datasets: [
        {
          label: "Total Expenses ($)",
          data: lineData,
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
      labels: categoryLabels,
      datasets: [
        {
          label: "Category-wise Expenses ($)",
          data: categoryData,
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
      labels: categoryLabels,
      datasets: [
        {
          data: categoryData,
          backgroundColor: ["#64ffda", "#00acc1", "#00838f", "#4dd0e1"],
        },
      ],
    },
  });
}
