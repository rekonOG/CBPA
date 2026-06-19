import { CssBaseline, ThemeProvider } from "@mui/material";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import useThemeMode from "./hooks/useThemeMode";
import About from "./pages/About";
import Dashboard from "./pages/Dashboard";
import Insights from "./pages/Insights";
import Landing from "./pages/Landing";
import Preview from "./pages/Preview";
import ProductAnalysis from "./pages/ProductAnalysis";
import ProductUpload from "./pages/ProductUpload";
import Results from "./pages/Results";
import Segments from "./pages/Segments";
import Upload from "./pages/Upload";
import getTheme from "./theme";

// Route setup keeps the landing page separate from the dashboard shell.
const App = () => {
  const { mode, toggleMode } = useThemeMode();
  const theme = getTheme(mode);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />

          <Route element={<AppLayout mode={mode} onToggleTheme={toggleMode} />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/upload-product" element={<ProductUpload />} />
            <Route path="/product-analysis" element={<ProductAnalysis />} />
            <Route path="/preview" element={<Preview />} />
            <Route path="/results" element={<Results />} />
            <Route path="/segments" element={<Segments />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/about" element={<About />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default App;
