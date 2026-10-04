// Compile Vue templates for the client renderer; tests provide an in-memory host.
export default {
  name: 'vue-memory-host',
  transformMode: 'web',
  setup() { return { teardown() {} } },
}
