<template>
  <section class="card mb-3">
    <div class="card-body p-3">
      <Bar :data="chartData" :options="options"></Bar>
    </div>
  </section>
</template>

<script>
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)


export default {
  components: { Bar },
  mounted() {
    // this.renderChart(this.chartData, this.options);
  },
  props: {
    chartData: {
      type: Object,
      default: null
    },
    options: {
      type: Object,
      default: null
    }
  }
};
</script>
