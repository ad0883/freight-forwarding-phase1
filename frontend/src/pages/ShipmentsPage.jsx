import { Plus, Search } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/client.js';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';

function ShipmentsPage() {
  const navigate = useNavigate();
  const [shipments, setShipments] = useState([]);
  const [search, setSearch] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (search) params.search = search;
      if (includeArchived) params.include_archived = true;
      const response = await api.get('/shipments', { params });
      setShipments(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load shipments');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timeout = setTimeout(load, 250);
    return () => clearTimeout(timeout);
  }, [search, includeArchived]);

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Shipments</p>
          <h1>Shipment List</h1>
        </div>
        <Link className="primary-button" to="/shipments/new">
          <Plus size={18} />
          <span>Create</span>
        </Link>
      </div>

      <div className="toolbar">
        <div className="search-box">
          <Search size={18} />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search shipment, line, port, commodity"
          />
        </div>
        <label className="checkbox-label compact-toggle">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(event) => setIncludeArchived(event.target.checked)}
          />
          Include Archived
        </label>
      </div>

      <ErrorState message={error} onRetry={load} />

      {loading && !shipments.length ? (
        <LoadingState label="Loading shipments..." />
      ) : (
        <div className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Shipment ID</th>
                  <th>Type</th>
                  <th>Shipping Line</th>
                  <th>Origin</th>
                  <th>Destination</th>
                  <th>Commodity</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {shipments.map((shipment) => (
                  <tr key={shipment.id} className="clickable-row" onClick={() => navigate(`/shipments/${shipment.id}`)}>
                    <td><strong>{shipment.shipment_code}</strong></td>
                    <td>{shipment.type}</td>
                    <td>{shipment.shipping_line || '-'}</td>
                    <td>{shipment.origin_port || '-'}</td>
                    <td>{shipment.dest_port || '-'}</td>
                    <td>{shipment.commodity || '-'}</td>
                    <td>
                      <span className={`badge status-${shipment.status}`}>{shipment.status}</span>
                      {shipment.is_archived && <span className="badge status-archived">Archived</span>}
                    </td>
                  </tr>
                ))}
                {!shipments.length && !loading && (
                  <tr>
                    <td colSpan="7">
                      <EmptyState title="No shipments found" detail="Try adjusting your search or create a new shipment." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default ShipmentsPage;
