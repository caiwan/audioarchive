<template>

  <div id="spinner" :class="{ visible: isLoading }"></div>

  <!-- Top bar and Menu -->
  <nav class="navbar navbar-expand-lg navbar-light bg-light p-1">
    <div class="container-fluid">

      <a class="navbar-brand" href="#">
        <img src="./assets/logo.png" alt="" width="40" height="40">
        Tapearchive
      </a>

      <button class="navbar-toggler" type="button" @click="toggleSidebar()">
        <span class="navbar-toggler-icon"></span>
      </button>

      <div class="navbar-collapse" id="navbarSupportedContent" :class="{'collapse': !showSidebar}">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0" v-if="!isInitializing">
          <li class="nav-item">
            <a class="nav-link active" href="#">Home</a>
            <!-- <a class="nav-link active" href="#" @click="testScnackbar()">Test snackbar</a> -->
          </li>

        </ul>
      </div>
    </div>
  </nav>

  <!-- Main content -->
  <main class="container-fluid p-3">

    <router-view v-if="!isInitializing" />
  </main>

  <!-- Footer with snackbar -->
  <footer class="drawer-transition">
    <div id="snackbar" :class="{ 'snackbar-on': showSnackbar }" @click="dismissSnackbar">
      <ul>
        <li v-for="(message, index) in snackbarMessages" :key="index">{{ message }}</li>
      </ul>
    </div>
  </footer>

</template>

<script>
import {
  mapState,
  //mapActions, 
  mapMutations,
  mapGetters,
} from 'vuex';

export default {
  name: 'App',
  components: {
  },
  computed: {
    ...mapState('UI', ['showSidebar', 'showSnackbar', 'snackbarMessages']),
    ...mapGetters('UI', ['isLoading']),
    // ...mapGetters('User', ['isLoggedIn']),
    ...mapState('App', ['isInitializing'])
  },
  methods: {
    // ...mapActions('User', ['fetchProfile']),
    ...mapMutations('App', ['initialized']),
    dismissSnackbar() {
      this.$store.commit('UI/pullSnackbar');
      console.log('dismiss');
    },
    toggleSidebar () {
      this.$store.commit('UI/toggle', 'showSidebar');
    },
    testScnackbar(){
      this.$store.dispatch('UI/pushIOError', 'Hello World');
    }
  },
  async created() {
    // await io.initialized;
    // this.fetchProfile();
    this.initialized();
  }
}
</script>

<style  lang="scss">
@import "./scss/app.scss";

footer {
  position: fixed;
  // width: 100%;
  left: 15px;
  right: 15px;
  bottom: 0px;

  #snackbar {
    position: relative;
    bottom: 30px;
    visibility: hidden;
    // min-width: 250px;
    // width: auto;
    margin: 0 auto;
    background-color: $warning;
    color: $gray-800;
    text-align: center;
    border-radius: 4px;
    padding: 16px;
    z-index: 20;

    @keyframes fadein {
      from {
        bottom: 0;
        opacity: 0;
      }

      to {
        bottom: 30px;
        opacity: 1;
      }
    }

    @keyframes fadeout {
      from {
        bottom: 30px;
        opacity: 1;
      }

      to {
        bottom: 0;
        opacity: 0;
      }
    }

    &.snackbar-on {
      visibility: visible !important;
      // animation: fadein 0.5s, fadeout 0.5s 2.5s;
      animation: fadein 0.5s;
    }

    ul {
      margin: 0px;
      padding: 0px;
      list-style-type: none;

      li {
        padding: 0px;
        margin: 0.5em 0em 0.5em 0em;
      }
    }
  }
}

#spinner {
  position: fixed;
  visibility: hidden;
  z-index: 60;

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }

    100% {
      transform: rotate(360deg);
    }
  }

  &::after {
    content: "";
    position: fixed;
    width: 96px;
    height: 96px;
    top: calc(50% - 48px);
    left: calc(50% - 48px);
    border-radius: 50%;
    border: 8px solid $cyan;
    border-left-color: transparent;
    animation: spin 2s infinite linear;
  }

  &.visible {
    visibility: visible;
  }
}
</style>
