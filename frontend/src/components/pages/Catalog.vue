<template>
    <section class="card mb-3">
      <div class="card-body p-3">
  
        <div class="input-group input-group-lg">
  
          <div class="input-group-prepend">
            <button type="button" class="btn btn-primary btn-lg" @click="openScan">Scan code</button>
          </div>
  
          <input class="form-control form-control-lg" type="text" placeholder="Catalog code" v-model="searchCode">
  
          <div class="input-group-append">
            <button type="button" class="btn btn-primary btn-lg" @click="doSerarch">Search</button>
          </div>
        </div>
      </div>
    </section>
  
    <!-- --- -->
    <qr-scan ref="qrscan" @codeRead="codeRead" />
    <!-- --- -->
  
    <section class="card  mb-3">
      <div class="card-body p-3">
        Search results
      </div>
    </section>
  
    <!-- --- -->
  </template>
  
  <script>
  import QRScan from '@/components/views/QRScan.vue';
  export default {
    name: 'Home',
  
    components: {
      "qr-scan": QRScan
    },
  
    data() {
      return { searchCode: "" };
    },
    methods: {
      openScan() {
        this.$refs.qrscan.open();
      },
  
      codeRead(code) {
        this.searchCode = code;
        this.doSerarch();
      },
  
      doSerarch() {
        // pass
      }
  
    },
  }
  </script>
  
  <style scoped></style>
  
  