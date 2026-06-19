import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Bootstrap the React application using the modern root API.
const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
