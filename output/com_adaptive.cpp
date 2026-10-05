/**
 * @file InstanceIdentifier.cpp
 * @brief Implementation of the Instance Identifier mechanism within the Application Manager (AM) module.
 * 
 * This file provides the implementation for managing unique identifiers assigned to instances of 
 * Software Components (SWC), Runtime Environment (RTE) connections, and other adaptive platform entities.
 * The identifier space is managed by the Application Manager to ensure uniqueness across the system.
 * 
 * @note This implementation adheres to the AUTOSAR Adaptive Platform Specification regarding 
 *       instance identification and allocation strategies.
 */

#include "Am_InstId.h"
#include "Am_InstanceManager.h"
#include "Am_InternalTypes.h"
#include <algorithm>
#include <vector>
#include <string>
#include <cstring>

namespace Am {

    // =========================================================================================================
    // Internal Helper Structures
    // =========================================================================================================

    /**
     * @struct InstIdEntry
     * @brief Represents a single entry in the internal mapping table used to track allocated IDs.
     */
    struct InstIdEntry {
        uint32_t id;
        std::string name;
        bool isValid;
        
        InstIdEntry() : id(0xFFFFFFFFU), isValid(false) {}
    };

    // =========================================================================================================
    // Public API Implementation
    // =========================================================================================================

    /**
     * @brief Allocates a new unique instance ID from the available pool.
     * 
     * This function searches through the list of free IDs and assigns one that has not been 
     * previously allocated. If no free IDs remain, it returns AM_STATUS_NO_FREE_INST_ID.
     * 
     * @param[out] pNewId Pointer to the variable where the newly allocated ID will be stored.
     * @return Am_Status Status of the operation. Returns AM_STATUS_OK on success, otherwise an error status.
     */
    Am_Status Am_AllocateInstanceId(uint32_t* pNewId) {
        if (pNewId == nullptr) {
            return AM_STATUS_INVALID_PARAMETER;
        }

        // Scan the global registry for the first valid but unallocated slot
        auto& registry = ApplicationManager::getInstance().getRegistry();
        
        for (auto& entry : registry.m_entries) {
            if (!entry.isValid) {
                entry.id = static_cast<uint32_t>(registry.m_freeCounter);
                entry.isValid = true;
                
                *pNewId = entry.id;
                return AM_STATUS_OK;
            }
        }

        return AM_STATUS_NO_FREE_INST_ID;
    }

    /**
     * @brief Releases a previously allocated instance ID back into the pool.
     * 
     * This function marks the specified ID as invalid/available for future allocations.
     * It does not guarantee immediate reuse by another thread due to lack of synchronization primitives 
     * in this specific snippet (typically handled by RTOS mutexes in full implementation).
     * 
     * @param instId The instance ID to release.
     * @return Am_Status Status of the operation. Returns AM_STATUS_OK on success.
     */
    Am_Status Am_FreeInstanceId(uint32_t instId) {
        auto& registry = ApplicationManager::getInstance().getRegistry();
        
        for (auto& entry : registry.m_entries) {
            if (entry.id == instId && entry.isValid) {
                entry.isValid = false;
                return AM_STATUS_OK;
            }
        }

        return AM_STATUS_NOT_FOUND;
    }

    /**
     * @brief Checks if a given instance ID is currently allocated/valid.
     * 
     * @param instId The instance ID to check.
     * @return true if the ID is currently allocated and valid.
     * @return false if the ID is not found or already freed.
     */
    bool Am_IsInstanceIdAllocated(uint32_t instId) {
        auto& registry = ApplicationManager::getInstance().getRegistry();
        
        for (const auto& entry : registry.m_entries) {
            if (entry.id == instId && entry.isValid) {
                return true;
            }
        }
        return false;
    }

    /**
     * @brief Retrieves the human-readable name associated with an instance ID.
     * 
     * @param instId The instance ID to query.
     * @param[out] pName Buffer to store the name string. Must have sufficient size.
     * @param bufferSize Size of the buffer provided.
     * @return Am_Status Status of the operation.
     */
    Am_Status Am_GetInstanceIdName(uint32_t instId, char* pName, uint16_t bufferSize) {
        if (pName == nullptr || bufferSize <= 0) {
            return AM_STATUS_INVALID_PARAMETER;
        }

        auto& registry = ApplicationManager::getInstance().getRegistry();
        
        for (const auto& entry : registry.m_entries) {
            if (entry.id == instId && entry.isValid) {
                strncpy(pName, entry.name.c_str(), bufferSize - 1);
                pName[bufferSize - 1] = '\0';
                return AM_STATUS_OK;
            }
        }

        return AM_STATUS_NOT_FOUND;
    }

    // =========================================================================================================
    // Internal Registry Management
    // =========================================================================================================

    /**
     * @class InstanceRegistry
     * @brief Manages the state of all active instance identifiers within the application context.
     */
    class InstanceRegistry {
    public:
        InstanceRegistry() : m_nextFreeId(1) {
            // Initialize the registry with a reasonable default capacity based on typical SWC counts
            // In production, this might be dynamically sized or fixed at compile time limits.
            m_entries.reserve(MAX_NUMBER_OF_APPLICATIONS + MAX_NUMBER_OF_RTE_CONNECTIONS);
            
            // Pre-populate entries as invalid
            for(size_t i=0; i<m_entries.size(); ++i) {
                m_entries[i].isValid = false;
            }
        }

        ~InstanceRegistry() = default;

        void addEntry(const std::string& name) {
            if (m_nextFreeId >= m_entries.size()) {
                // Dynamic expansion logic would go here in a real implementation
                // For now, we assume static sizing covers the use case defined in spec.
                throw std::out_of_range("InstanceRegistry overflow");
            }
            
            m_entries[m_nextFreeId-1].name = name;
            m_entries[m_nextFreeId-1].id = m_nextFreeId;
            m_entries[m_nextFreeId-1].isValid = true;
            m_nextFreeId++;
        }

        void removeEntry(uint32_t id) {
            for(auto& entry : m_entries) {
                if(entry.id == id) {
                    entry.isValid = false;
                    break;
                }
            }
        }

        const std::vector<InstIdEntry>& getEntries() const {
            return m_entries;
        }

    private:
        std::vector<InstIdEntry> m_entries;
        uint32_t m_nextFreeId;
    };

} // namespace Am
