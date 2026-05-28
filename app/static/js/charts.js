// Круговая диаграмма расходов по категориям
if (document.getElementById('pieChart') && pieValues && pieValues.length > 0) {
  new Chart(document.getElementById('pieChart'), {
    type: 'doughnut',
    data: {
      labels: pieLabels,
      datasets: [{
        data: pieValues,
        backgroundColor: pieColors,
        borderWidth: 2,
        borderColor: '#fff',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'right', labels: { font: { size: 12 }, padding: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed.toLocaleString('ru-RU')} ₽`
          }
        }
      }
    }
  });
}

// Линейный график динамики трат по дням
if (document.getElementById('lineChart') && dailyValues && dailyValues.length > 0) {
  const formattedLabels = dailyLabels.map(d => {
    const [y, m, day] = d.split('-');
    return `${day}.${m}`;
  });

  new Chart(document.getElementById('lineChart'), {
    type: 'line',
    data: {
      labels: formattedLabels,
      datasets: [{
        label: 'Расходы',
        data: dailyValues,
        borderColor: '#ef4444',
        backgroundColor: 'rgba(239,68,68,.12)',
        tension: 0.3,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: '#ef4444',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.parsed.y.toLocaleString('ru-RU')} ₽`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => v.toLocaleString('ru-RU') + ' ₽' }
        }
      }
    }
  });
}
