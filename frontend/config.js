// Deployment configuration is source-controlled, never taken from links or storage.
// Set this to your HTTPS API origin for a separately hosted frontend.
const DEPLOYED_API_ORIGIN = "";
try { window.localStorage.removeItem("medictime.apiBaseUrl"); } catch {}
const apiOrigin = DEPLOYED_API_ORIGIN || window.location.origin;
const parsedOrigin = new URL(apiOrigin);
if (parsedOrigin.protocol !== "https:" &&
    !(parsedOrigin.protocol === "http:" && ["localhost", "127.0.0.1"].includes(parsedOrigin.hostname))) {
  throw new Error("MedicTime requires an HTTPS API origin.");
}
window.MEDICTIME_CONFIG = Object.freeze({ API_BASE_URL: parsedOrigin.origin });
