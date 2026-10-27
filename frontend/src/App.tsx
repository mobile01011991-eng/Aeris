import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AnalyzePage } from "./pages/AnalyzePage";
import { ResultsHubPage } from "./pages/ResultsHubPage";
import { ResultsPage } from "./pages/ResultsPage";
import { ToolReportPage } from "./pages/ToolReportPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<AnalyzePage />} />
          <Route path="analyze" element={<Navigate to="/" replace />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="results/:sampleId" element={<ResultsHubPage />} />
          <Route path="results/:sampleId/:toolKey" element={<ToolReportPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
