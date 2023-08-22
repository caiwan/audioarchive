<template lang="">
  <section class="modal fade" :class="{ 'show': isOpen }" :style="isOpen?{'display':'block'} :{'display':'none'}" tabindex="-1">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">Scan QR code</h5>
          <!-- <button type="button" class="close" @click="close">
            <span aria-hidden="true">&times;</span>
          </button> -->
        </div>
        <div class="modal-body">
        <StreamBarcodeReader
            @init="onInit"
            @decode="onDecode"
            @loaded="onLoaded"
        />
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-primary" @click="close">Save changes</button>
          <button type="button" class="btn btn-secondary" @click="close">Close</button>
        </div>
      </div>
    </div>
  </section>
</template>
<script>
import { StreamBarcodeReader } from "vue-barcode-reader";
export default {
    // TODO https://olefyrenko.com/blog/how-to-add-a-qr-and-barcode-scanner-to-your-vue-js-app
    // https://gruhn.github.io/vue-qrcode-reader/api/QrcodeStream.html#events

    // TODO Load component dynamically https://stackoverflow.com/questions/53406350/vue-import-vue-components-dynamically
    
    name: 'QRScan',
    components: {
        StreamBarcodeReader
    },
    data() {
        return {
            isOpen: false
        }
    },
    methods: {
        open() {
            this.isOpen = true;
        },
        close() {
            this.isOpen = false;
        },

        async onInit(promise) {
            // show loading indicator

            try {
                const { capabilities } = await promise;
                console.log(capabilities);
                // successfully initialized
            } catch (error) {
                this.$store.dispatch('UI/pushIOError', error.name);
                // if (error.name === 'NotAllowedError') {
                //     // user denied camera access permisson
                // } else if (error.name === 'NotFoundError') {
                //     // no suitable camera device installed
                // } else if (error.name === 'NotSupportedError') {
                //     // page is not served over HTTPS (or localhost)
                // } else if (error.name === 'NotReadableError') {
                //     // maybe camera is already in use
                // } else if (error.name === 'OverconstrainedError') {
                //     // did you requested the front camera although there is none?
                // } else if (error.name === 'StreamApiNotSupportedError') {
                //     // browser seems to be lacking features
                // }
            } finally {
                // hide loading indicator
            }
        },

        onDecode(text) {
            console.log(`Decode text from QR code is ${text}`)
        },

        onLoaded() {
            console.log(`Ready to start scanning barcodes`)
        }

    },

}
</script>

<style scoped>

</style>