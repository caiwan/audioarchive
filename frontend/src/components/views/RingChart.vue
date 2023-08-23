<template>
  <section class="card mb-3">
    <div class="card-body p-3">
      <Doughnut :data="chartData" :options="options"></Doughnut>
    </div>
  </section>
</template>

<script>
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Doughnut } from 'vue-chartjs'
// import * as chartConfig from './chartConfig.js'

ChartJS.register(ArcElement, Tooltip, Legend)

export default {
  components: { Doughnut },
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