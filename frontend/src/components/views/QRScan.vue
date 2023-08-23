<template lang="">
  
  <section class="modal fade" :class="{ 'show': isOpen }" :style="isOpen?{'display':'block'} :{'display':'none'}" tabindex="-1">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">


          <div class="dropdown" :class="{ 'show': showInputSelector }">
            <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" @click="toggleInputSelector">
              {{currentDevice ? currentDevice.label: ""}}
            </button>
  
            <div class="dropdown-menu" :class="{ 'show': showInputSelector }">
              <template v-for="device in devices" :key="device.deviceId">
                <a class="dropdown-item" href="#" @click="selectInputDevice(device)">{{device.label}}</a>
            </template>
            </div>

          </div>

        </div>
        <div class="modal-body">
          
          <div class="scanner-container">
            <div v-show="!isLoading">
              <video poster="data:image/gif,AAAA" ref="scanner"></video>
              <div class="overlay-element"></div>
              <div class="laser"></div>
            </div>
          </div>

        </div>
        <div class="modal-footer">
          <h5>{{lastCodeRead}}</h5>
          <button type="button" class="btn btn-primary" :class="{'disabled' : canAccept}" @click="accept">Accept</button>
          <button type="button" class="btn btn-danger" :class="{'disabled' : canAccept}" @click="retry">Retry</button>
          <button type="button" class="btn btn-secondary" @click="close">Close</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script>

import { BrowserMultiFormatReader, Exception, NotFoundException } from "@zxing/library";
export default {
  name: 'QRScan',

  data() {
    return {
      isOpen: false,
      isLoading: true,
      codeReader: new BrowserMultiFormatReader(),
      isMediaStreamAPISupported: navigator && navigator.mediaDevices && "enumerateDevices" in navigator.mediaDevices,
      lastCodeRead: null,
      devices: [],
      currentDevice: null,
      showInputSelector: false
    }
  },

  computed: {
    canAccept() { return this.lastCodeRead == null },
  },

  beforeUnmount() {
    this.codeReader.reset();
  },

  methods: {
    async open() {
      this.isOpen = true;
      this.isLoading = true;
      this.showInputSelector = false;

      if (!this.isMediaStreamAPISupported) {
        this.$store.dispatch('UI/pushIOError', "Media Stream API is not supported");
        throw new Exception("Media Stream API is not supported");
      }

      this.devices = await this.codeReader.listVideoInputDevices();
      console.log("Available devices:", this.devices)

      this.currentDevice = this.devices ? this.devices[0] : null;
      console.log("Current device", this.currentDevice);

      this.start();
      this.$refs.scanner.oncanplay = (event) => {  // TODO: Event
        this.isLoading = false;
        console.log(event)
      };

    },

    start() {
      // const deviceId = this.currentDevice.deviceId ? this.currentDevice : null;
      const deviceId = null;

      this.codeReader.decodeOnceFromVideoDevice(deviceId, this.$refs.scanner, (result, error) => {
        if (result) {
          this.lastCodeRead = result.text;
          this.codeReader.stopContinuousDecode();
        } else {
          if (!(error instanceof NotFoundException)) {
            this.$store.dispatch('UI/pushIOError', error);
          }
        }
      })
    },

    accept() {
      this.$emit("codeRead", this.lastCodeRead);
      this.lastCodeRead = null;
      this.close();
    },

    retry() {
      this.lastCodeRead = null;
      this.start();
    },

    close() {
      this.codeReader.reset();
      this.isOpen = false;

    },

    toggleInputSelector() {
      this.showInputSelector = !this.showInputSelector;
    },

    selectInputDevice(device) {
      this.currentDevice = device;
      this.codeReader.reset();
      this.start();
      this.showInputSelector = false;
    }

  },

}
</script>


<style scoped>
video {
  max-width: 100%;
  max-height: 100%;
}

.scanner-container {
  position: relative;
}

.overlay-element {
  position: absolute;
  top: 0;
  width: 100%;
  height: 99%;
  background: rgba(30, 30, 30, 0.5);

  -webkit-clip-path: polygon(0% 0%, 0% 100%, 20% 100%, 20% 20%, 80% 20%, 80% 80%, 20% 80%, 20% 100%, 100% 100%, 100% 0%);
  clip-path: polygon(0% 0%, 0% 100%, 20% 100%, 20% 20%, 80% 20%, 80% 80%, 20% 80%, 20% 100%, 100% 100%, 100% 0%);
}

.laser {
  width: 60%;
  margin-left: 20%;
  background-color: tomato;
  height: 1px;
  position: absolute;
  top: 40%;
  z-index: 2;
  box-shadow: 0 0 4px red;
  -webkit-animation: scanning 2s infinite;
  animation: scanning 2s infinite;
}

@-webkit-keyframes scanning {
  50% {
    -webkit-transform: translateY(75px);
    transform: translateY(75px);
  }
}

@keyframes scanning {
  50% {
    -webkit-transform: translateY(75px);
    transform: translateY(75px);
  }
}
</style>




