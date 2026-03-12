import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import SchemaFinder from './pages/SchemaFinder';
import SchemaValidate from './pages/SchemaValidate';
import VersionCheck from './pages/VersionCheck';

function App() {
  return (
    <Router>
      <div className="flex h-screen bg-black">
        <Sidebar />
        <div className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<SchemaFinder />} />
            <Route path="/schema-finder" element={<SchemaFinder />} />
            <Route path="/schema-validate" element={<SchemaValidate />} />
            <Route path="/version-check" element={<VersionCheck />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
