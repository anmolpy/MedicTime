const hostname = window.location.hostname;
const isLocalHost = hostname === "localhost" || hostname === "127.0.0.1";
const params = new URLSearchParams(window.location.search);

let savedApiBaseUrl = "";
try {
  savedApiBaseUrl = window.localStorage.getItem("medictime.apiBaseUrl") || "";
} catch (error) {
  savedApiBaseUrl = "";
}

const queryApiBaseUrl = (params.get("api") || "").trim().replace(/\/$/, "");
if (queryApiBaseUrl) {
  try {
    window.localStorage.setItem("medictime.apiBaseUrl", queryApiBaseUrl);
  } catch (error) {
    // Ignore storage failures and keep the runtime override only.
  }
}

window.MEDICTIME_CONFIG = {
  API_BASE_URL: queryApiBaseUrl || savedApiBaseUrl || (isLocalHost ? "http://localhost:8000" : ""),
};
