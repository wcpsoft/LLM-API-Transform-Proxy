<template>
  <div class="service-status-view">
    <ServiceStatus />
  </div>
</template>

<script>
import ServiceStatus from '@/components/ServiceStatus.vue'

export default {
  name: 'ServiceStatusView',
  components: {
    ServiceStatus
  }
}
</script>

<style scoped>
.service-status-view {
  width: 100%;
  height: 100%;
}
</style>