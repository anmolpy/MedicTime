const hostname = window.location.hostname;
const isLocalHost = hostname === "localhost" || hostname === "127.0.0.1";

window.MEDICTIME_CONFIG = {
  API_BASE_URL: isLocalHost ? "http://localhost:8000" : "",
};
