import React from "react";
import PropTypes from "prop-types";


function ScheduledJobsTable({ jobs, onDelete, onDetails, onDownload }) {
  if (!jobs?.length) {
    return (
      <p className="text-muted text-center">
        No crawl jobs yet. Schedule a new crawl to see it here.
      </p>
    );
  }

  /** Human-readable schedule column */
  const fmtSchedule = (j) =>
    j.recurring
      ? `${j.frequency} (recurring)`
      : j.dateTime
      ? new Date(j.dateTime).toLocaleString()
      : "—";

  return (
    <div className="table-responsive">
      <table className="table table-striped table-hover align-middle">
        <thead className="table-light">
          <tr>
            <th style={{ minWidth: 180 }}>Job name</th>
            <th style={{ minWidth: 190 }}>Schedule</th>
            <th>Status</th>
            <th className="text-end" style={{ width: 210 }}>Actions</th>
          </tr>
        </thead>

        <tbody>
          {jobs.map((j) => (
            <tr key={j.id}>
              <td>{j.name || `(Job ${j.id})`}</td>
              <td>{fmtSchedule(j)}</td>
              <td>{j.status}</td>

              <td className="text-end">
                {/* View details (modal) */}
                {onDetails && (
                  <button
                    className="btn btn-outline-secondary btn-sm me-2"
                    onClick={() => onDetails(j.id)}
                  >
                    View Result
                  </button>
                )}

                {/* Download latest run */}
                {onDownload && j.latestRunId && (
                  <button
                    title="Download latest run (CSV)"
                    className="btn btn-outline-secondary btn-sm me-2"
                    onClick={() => onDownload(j.latestRunId)}
                  >
                    <span className="bi bi-download" />
                  </button>
                )}

                {/* Delete */}
                <button
                  className="btn btn-outline-danger btn-sm"
                  onClick={() => onDelete(j.id)}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

ScheduledJobsTable.propTypes = {
  jobs:       PropTypes.arrayOf(PropTypes.object).isRequired,
  onDelete:   PropTypes.func.isRequired,
  onDetails:  PropTypes.func,
  onDownload: PropTypes.func
};

export default ScheduledJobsTable;
