/**
 * @file DiagImpl.cpp
 * @brief Implementation of the AUTOSAR Adaptive Platform Diagnostic Service.
 * 
 * This file implements the core logic for the 'Diag' software component.
 * It provides functionality for logging events, retrieving stored logs,
 * clearing logs, and managing diagnostic configurations according to 
 * the ARA specification.
 * 
 * Namespace: ara::diag
 */

#include "ara/diag/Diag.hpp"
#include "ara/com/Com.hpp"
#include "ara/cfg/Cfg.hpp"
#include <algorithm>
#include <chrono>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <mutex>


namespace ara::diag {

// ============================================================================
// Internal Configuration Helper
// ============================================================================

static const std::string DIAG_LOG_FILE_PATH = "/tmp/adaptivediag.log"; // Default fallback if CFG not set
static const uint32_t DEFAULT_MAX_LOG_SIZE_BYTES = 1048576; // 1MB default

// ============================================================================
// Class: DiagService
// Description: Implements the main diagnostic service logic.
// ============================================================================

class DiagService : public com::IProvider {
public:
    /**
     * @brief Constructor for the Diagnostic Service.
     * Initializes internal state and retrieves configuration.
     */
    DiagService() 
        : m_logBuffer(), 
          m_maxBufferSize(DEFAULT_MAX_LOG_SIZE_BYTES),
          m_isInitialized(false) {}

    ~DiagService() override = default;

    // ------------------------------------------------------------------------
    // Interface Methods (from com::IProvider)
    // ------------------------------------------------------------------------

    bool start() override {
        if (m_isInitialized) return true;

        // Attempt to load configuration
        try {
            auto cfg = cfg::get("Diag");
            if (!cfg.empty()) {
                m_maxBufferSize = static_cast<uint32_t>(cfg["MaxLogSizeBytes"].toUInt());
            }
            
            // Initialize buffer with max size
            m_logBuffer.resize(m_maxBufferSize);
            m_currentPos = 0;
        } catch (...) {
            // If config fails, use defaults
            m_logBuffer.resize(m_maxBufferSize);
            m_currentPos = 0;
        }

        m_isInitialized = true;
        return true;
    }

    bool stop() override {
        m_isInitialized = false;
        m_logBuffer.clear();
        return true;
    }

    bool reset() override {
        if (!m_isInitialized) return false;
        
        m_logBuffer.clear();
        m_currentPos = 0;
        return true;
    }

    // ------------------------------------------------------------------------
    // Domain Specific Methods (Diag API)
    // ------------------------------------------------------------------------

    /**
     * @brief Logs a single event into the circular buffer.
     * @param event The event structure containing timestamp, level, id, and message.
     * @return true if successful, false otherwise.
     */
    bool logEvent(const Event& event) override {
        if (!m_isInitialized) return false;

        // Check buffer capacity before adding
        if (m_currentPos >= static_cast<int>(m_logBuffer.size())) {
            // Buffer full, drop oldest entry (circular behavior)
            m_logBuffer.erase(0, 1);
        } else {
            // Shift existing entries down if necessary (simple shift strategy)
            // In production, a ring buffer approach might be more efficient than vector erase
            if (m_currentPos > 0) {
                m_logBuffer.erase(0, 1);
            }
        }

        // Add new event at current position
        m_logBuffer.push_back(event);
        m_currentPos++;

        return true;
    }

    /**
     * @brief Retrieves all logged events since the last call to getLog().
     * Note: In a real-time system, this should ideally support offset-based retrieval
     * to avoid re-reading old data. Here we implement a simple copy for demonstration.
     * 
     * @param[out] outVector Vector to store retrieved events.
     * @return true if successful, false otherwise.
     */
    bool getLog(std::vector<Event>& outVector) override {
        if (!m_isInitialized || outVector.capacity() == 0) return false;

        // Copy current buffer content to output
        outVector.insert(outVector.end(), m_logBuffer.begin(), m_logBuffer.end());
        
        return true;
    }

    /**
     * @brief Clears the entire log buffer.
     * @return true if successful, false otherwise.
     */
    bool clearLog() override {
        if (!m_isInitialized) return false;
        m_logBuffer.clear();
        m_currentPos = 0;
        return true;
    }

    /**
     * @brief Gets the current number of events in the buffer.
     * @return uint32_t Count of events.
     */
    uint32_t getLogCount() const override {
        return static_cast<uint32_t>(m_logBuffer.size());
    }

    /**
     * @brief Sets the maximum size of the log buffer.
     * @param newSize New maximum size in bytes.
     * @return true if successful, false otherwise.
     */
    bool setMaxLogSize(uint32_t newSize) override {
        if (!m_isInitialized) return false;
        
        // Ensure new size is reasonable
        if (newSize <= 0 || newSize > 10 * 1024 * 1024) { // Max 10MB limit
            return false;
        }

        m_maxBufferSize = newSize;
        m_logBuffer.resize(newSize);
        return true;
    }

private:
    std::vector<Event> m_logBuffer;
    uint32_t           m_maxBufferSize;
    int                m_currentPos;
    bool               m_isInitialized;
};

// ============================================================================
// Factory / Singleton Pattern Implementation
// ============================================================================

std::unique_ptr<com::IProvider> createDiagService() {
    return std::make_unique<DiagService>();
}

// ============================================================================
// Public API Wrapper (Convenience functions matching typical usage patterns)
// ============================================================================

bool logDiagnosticEvent(const Event& event) {
    auto svc = createDiagService();
    if (svc && svc->start()) {
        return svc->logEvent(event);
    }
    return false;
}

std::vector<Event> retrieveLogs() {
    std::vector<Event> result;
    auto svc = createDiagService();
    if (svc && svc->start()) {
        svc->getLog(result);
    }
    return result;
}

bool clearAllLogs() {
    auto svc = createDiagService();
    if (svc && svc->start()) {
        return svc->clearLog();
    }
    return false;
}

uint32_t getLogCount() {
    auto svc = createDiagService();
    if (svc && svc->start()) {
        return svc->getLogCount();
    }
    return 0u;
}

} // namespace diag
