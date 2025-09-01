<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('{{ url_for("static", filename="pwa/sw.js") }}');
  });
}
</script>