// App.vue
<template>
  <div class="container mt-5">
    <div class="row">
      <div class="col-md-4">
        <ring-chart :chartData="ringChartData1" :options="chartOptions"></ring-chart>
      </div>
      <div class="col-md-4">
        <ring-chart :chartData="ringChartData2" :options="chartOptions"></ring-chart>
      </div>
      <div class="col-md-4">
        <line-chart :chartData="lineChartData" :options="chartOptions"></line-chart>
      </div>
    </div>
  </div>
</template>

<script>
import RingChart from '@/components/views/RingChart.vue';
import LineChart from '@/components/views/LineChart.vue';

export default {
  components: {
    RingChart,
    LineChart
  },
  data() {
    return {
      ringChartData1: {
        labels: ['Red', 'Blue', 'Yellow'],
        datasets: [{
          data: [10, 20, 70],
          backgroundColor: ['red', 'blue', 'yellow']
        }]
      },
      ringChartData2: {
        labels: ['Green', 'Purple', 'Orange'],
        datasets: [{
          data: [20, 30, 50],
          backgroundColor: ['green', 'purple', 'orange']
        }]
      },
      lineChartData: {
        labels: ['January', 'February', 'March', 'April', 'May'],
        datasets: [{
          label: 'Sample Data',
          backgroundColor: '#f2f2f2',
          borderColor: 'blue',
          data: [10, 40, 25, 75, 50]
        }]
      },
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false
      }
    };
  }
};
</script>
