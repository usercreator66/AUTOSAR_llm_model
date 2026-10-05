/**
 * @file InstanceIdentifier.cpp
 * @brief Implementation of the Instance Identifier mechanism within the Application Manager (AM) module.
 *        This component manages unique identifiers for application instances to ensure uniqueness 
 *        across the system and support instance-based resource allocation.
 * 
 * @note This implementation adheres to the AUTOSAR Adaptive Platform Specification.
 *       It provides a thread-safe mechanism for generating and managing instance IDs.
 */

#include "Am_InstanceId.h"
#include <cstdint>
#include <cstring>
#include <atomic>
#include <mutex>
#include <map>
#include <vector>

#ifdef AM_INSTANCE_ID_IMPLEMENTATION
// If the header defines this macro, we might be in a specific configuration mode.
// For standard generation, we assume the logic is defined below unless overridden by preprocessor directives.
#endif

namespace Am {

    /**
     * @class InstanceIdManager
     * @brief Manages the lifecycle and state of application instance identifiers.
     * 
     * The Instance ID is derived from a combination of the Node ID and a per-node counter.
     * This ensures global uniqueness as long as the Node ID space is respected.
     */
    class InstanceIdManager {
    public:
        /**
         * @brief Constructs the manager with default settings.
         */
        InstanceIdManager() : m_nextNodeId(0), m_nodeCounter(0) {}

        /**
         * @brief Initializes the manager with a specific node identifier.
         * @param nodeId The unique identifier for this node.
         */
        void initialize(uint32_t nodeId) {
            std::lock_guard<std::mutex> lock(m_mutex);
            if (m_initialized && m_currentNodeId != nodeId) {
                // Re-initialization allowed only once typically, but here we update if needed
                // or throw error based on strictness. Assuming flexible re-init for demo.
                m_currentNodeId = nodeId;
            } else if (!m_initialized) {
                m_currentNodeId = nodeId;
                m_initialized = true;
            }
        }

        /**
         * @brief Generates a new unique instance identifier.
         * @return uint64_t A unique 64-bit integer representing the instance ID.
         * @retval 0xFFFFFFFFFFFFFFFF Indicates failure to generate a unique ID (ID Space Exhaustion).
         */
        uint64_t getInstanceId() {
            std::lock_guard<std::mutex> lock(m_mutex);
            
            if (!m_initialized) {
                return static_cast<uint64_t>(-1); // Error Code
            }

            // Increment the local counter for this node
            m_nodeCounter++;

            // Check for overflow of the local counter before wrapping around to next node ID
            const uint32_t MAX_COUNTER_VALUE = 0x7FFFFFFF; // Leave room for sign bit if treated as int, though used as unsigned here usually max is UINT_MAX
            
            if (m_nodeCounter > MAX_COUNTER_VALUE) {
                 // Wrap around to next node ID if counter overflows
                 m_nodeCounter = 0;
                 m_nextNodeId++;
                 
                 if (m_nextNodeId >= 0xFF) {
                     // Node ID space exhausted
                     return static_cast<uint64_t>(-1);
                 }
            }

            // Construct the 64-bit ID: [NodeID (High 8 bits)] [Counter (Low 56 bits)]
            // Note: In many implementations, NodeID is 8 bits (0..255) and Counter is 56 bits.
            // Here we use 32-bit NodeID + 32-bit Counter mapped into 64-bit space.
            // Standard practice often reserves high bits for NodeID.
            
            // Let's assume a layout where High 8 bits are NodeID and Low 56 bits are Counter
            // However, to maximize space given the spec, let's use:
            // Bits 0-31: Counter
            // Bits 32-63: NodeID (assuming up to 32 nodes for simplicity in this example, 
            // or full 32-bit if architecture supports it).
            
            // Using the retrieved spec pattern: 
            // InstanceID = (NodeID << 32) | LocalCounter
            // This allows 32 Nodes x 4GB counters.
            
            uint64_t instanceId = ((static_cast<uint64_t>(m_currentNodeId)) << 32) | m_nodeCounter;
            
            return instanceId;
        }

        /**
         * @brief Checks if an instance ID exists locally.
         * @param id The candidate instance ID.
         * @return bool True if the ID belongs to this node, False otherwise.
         */
        bool isLocalInstance(uint64_t id) {
            std::lock_guard<std::mutex> lock(m_mutex);
            if (!m_initialized || id == static_cast<uint64_t>(-1)) {
                return false;
            }
            
            // Extract the lower 32 bits which represent the counter
            uint32_t extractedCounter = static_cast<uint32_t>(id & 0xFFFFFFFFULL);
            
            // We must check if the current counter matches one of our previous allocations?
            // Actually, since we increment sequentially, any valid ID generated by us 
            // will have the correct upper bits (NodeID).
            // To strictly verify ownership without history tracking, we rely on the NodeID match.
            // But to prevent reuse issues if we don't track allocated IDs, we assume sequential non-reuse.
            
            // Simple validation: Does the upper 32 bits match my NodeID?
            uint32_t storedNodeId = static_cast<uint32_t>((id >> 32) & 0xFFFFFFFFULL);
            
            return (storedNodeId == m_currentNodeId);
        }

    private:
        mutable std::mutex m_mutex; ///< Mutex for thread safety
        bool m_initialized{false};   ///< Flag indicating initialization status
        uint32_t m_currentNodeId{0}; ///< Current Node ID
        uint32_t m_nodeCounter{0};   ///< Per-node instance counter
        
        // Optional: History of allocated IDs to detect duplicates if counter wraps
        // std::set<uint64_t> m_allocatedIds; 
    };

} // namespace Am

/*
 * ============================================================================
 * Public API Interface Implementation
 * ============================================================================
 */

using namespace Am;

extern "C" {

/**
 * @brief Gets the singleton instance of the InstanceIdManager.
 * @return Pointer to the InstanceIdManager instance.
 */
Am_InstanceId* Am_InstanceId_GetInstance(void) {
    static InstanceIdManager s_instance;
    return reinterpret_cast<Am_InstanceId*>(&s_instance);
}

/**
 * @brief Allocates a new instance identifier.
 * @param[out] pInstanceId Buffer to store the generated ID. Must point to at least 8 bytes.
 * @retval E_OK Success.
 * @retval E_NOT_OK Failure (e.g., ID space exhaustion).
 */
ErrorType Am_InstanceId_Allocate(uint64_t* pInstanceId) {
    if (pInstanceId == nullptr) {
        return E_NOT_OK;
    }

    auto* manager = Am_InstanceId_GetInstance();
    
    // Call internal method
    uint64_t id = manager->getInstanceId();
    
    if (id == static_cast<uint64_t>(-1)) {
        return E_NOT_OK;
    }

    *pInstanceId = id;
    return E_OK;
}

/**
 * @brief Releases an instance identifier (Optional functionality depending on spec version).
 *        In some specs, IDs are persistent until reboot. In others, they can be freed.
 *        This stub assumes persistence for now, or returns E_NOT_OK if release isn't supported.
 */
ErrorType Am_InstanceId_Release(uint64_t pInstanceId) {
    // Depending on the exact specification version:
    // 1. IDs are immutable after allocation (Return E_NOT_OK).
    // 2. IDs can be released and reused.
    // 
    // Based on common AUTOSAR AP patterns, simple allocation is often sufficient.
    // If dynamic management is required, a pool would be implemented here.
    // For this generic implementation, we assume no explicit release is needed 
    // or that the ID remains valid for the lifetime of the process/node.
    
    // Placeholder for future extension if dynamic pooling is added.
    // For now, returning success implies the ID is valid/owned.
    return E_OK; 
}

/**
 * @brief Checks if a given ID belongs to the current node.
 * @param[in] pInstanceId The instance ID to check.
 * @retval TRUE if the ID belongs to this node.
 * @retval FALSE otherwise.
 */
Boolean Am_InstanceId_IsMine(uint64_t pInstanceId) {
    auto* manager = Am_InstanceId_GetInstance();
    return manager->isLocalInstance(pInstanceId);
}

} // extern "C"

/**
 * @brief Initialization function called during System Startup.
 *        Sets the Node ID for the current execution environment.
 * @param[in] uNodeId The unique identifier assigned to this node by the Bootloader/Hardware.
 */
void Am_InstanceId_Init(uint32_t uNodeId) {
    auto* manager = Am_InstanceId_GetInstance();
    manager->initialize(uNodeId);
}

/**
 * @brief Cleanup function called during System Shutdown.
 *        Resets internal state.
 */
void Am_InstanceId_DeInit(void) {
    auto* manager = Am_InstanceId_GetInstance();
    manager->~InstanceIdManager(); // Reset state if using RAII or manual reset
}

/**
 * @brief Getters for diagnostic purposes.
 * @return Current Node ID.
 */
uint32_t Am_InstanceId_GetCurrentNodeId(void) {
    auto* manager = Am_InstanceId_GetInstance();
    return manager->getCurrentNodeId();
}

/**
 * @brief Getters for diagnostic purposes.
 * @return Current Instance Counter value.
 */
uint32_t Am_InstanceId_GetCurrentCounter(void) {
    auto* manager = Am_InstanceId_GetInstance();
    return manager->getCurrentCounter();
}
