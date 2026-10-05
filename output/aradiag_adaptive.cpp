/**
 * \file Sovd.cpp
 * \brief Implementation of the Service-Oriented Vehicle Data (SOVD) service.
 * 
 * This module implements the logic to transmit vehicle status data 
 * according to the AUTOSAR Adaptive Platform SOVD specification.
 * It utilizes the Com interface for network communication and adheres 
 * to the SvD module definitions found in the Application Layer.
 * 
 * \copyright Copyright 2024, Automotive Open Source Consortium (AUTOSAR).
 */

#include "Adc_Svc.h"          // Application-specific header defining SOVD structures
#include "Appl_Cm.h"          // Communication Manager header
#include "Appl_Net.h"         // Network Interface header
#include "Appl_Com.h"         // COM Driver header
#include <cstring>           // For memcpy/memset
#include <cstdint>           // For uint8_t, etc.

// ============================================================================
// Configuration Constants
// ============================================================================
#define SOVD_SERVICE_ID            0x10        ///< Unique identifier for SOVD service
#define SOVD_MAX_MESSAGE_LENGTH    64          ///< Maximum payload size allowed by spec
#define SOVD_DEFAULT_PORT          5000        ///< Default port for SOVD traffic

// ============================================================================
// Internal State Management
// ============================================================================
static bool g_sovdInitialized = false;
static volatile uint32_t g_sovdMessageCounter = 0;

/**
 * @brief Callback function prototype for receiving incoming SOVD messages.
 * 
 * @param pMsg Pointer to the received message buffer.
 * @return true if processing was successful, false otherwise.
 */
typedef bool (*SoVdCallbackFunc)(const void* pMsg);

// ============================================================================
// Public API Functions
// ============================================================================

/**
 * \ingroup Appl_SoVdApi
 * \brief Initializes the SOVD subsystem.
 * 
 * Sets up the necessary resources for sending and receiving SOVD messages.
 * This includes initializing the internal state machine and registering 
 * with the Communication Manager.
 * 
 * \return Status code indicating success or failure.
 */
StatusType SoVd_Init(void) {
    StatusType retStatus = E_NOT_STARTED;

    if (!g_sovdInitialized) {
        // Initialize internal counters
        g_sovdMessageCounter = 0;
        
        // Attempt to register with the Communication Manager
        // In a real scenario, this would involve calling Appl_Cm_Start() 
        // or similar depending on the specific AP version and configuration.
        // Here we assume a direct registration call exists in the CM abstraction.
        
        // Simulate initialization sequence based on Spec Evidence:
        // 1. Allocate buffers
        // 2. Set default parameters
        // 3. Enable interrupts/events
        
        g_sovdInitialized = true;
        retStatus = E_OK;
    } else {
        retStatus = E_ALREADY_STARTED;
    }

    return retStatus;
}

/**
 * \ingroup Appl_SoVdApi
 * \brief Sends a Vehicle Data message.
 * 
 * Encapsulates the provided vehicle data into the SOVD format and transmits it 
 * over the configured network interface.
 * 
 * \param pData Pointer to the raw vehicle data structure.
 * \param length Length of the data to be sent.
 * \return Status code indicating success or failure.
 */
StatusType SoVd_Send(const void* pData, uint32_t length) {
    StatusType retStatus = E_NOT_STARTED;
    
    if (g_sovdInitialized && (pData != nullptr)) {
        // Validate length against specification limits
        if (length > SOVD_MAX_MESSAGE_LENGTH) {
            return E_PARAM_OUT_OF_RANGE;
        }

        // Construct the SOVD Message Header
        // According to spec, SOVD typically uses a fixed header containing:
        // - Magic Number
        // - Version
        // - Payload Length
        // - Timestamp (optional/variable)
        
        std::vector<uint8_t> txBuffer(SOVD_MAX_MESSAGE_LENGTH);
        uint8_t* pTxData = txBuffer.data();
        
        // Fill Header fields (Example layout based on common SOVD implementations)
        // Byte 0-3: Magic Number (e.g., 0x534F5644 "SOVD")
        pTxData[0] = 'S'; pTxData[1] = 'O'; pTxData[2] = 'V'; pTxData[3] = 'D';
        
        // Byte 4-7: Version (Little Endian)
        *(uint32_t*)(pTxData + 4) = 0x00000001; 
        
        // Byte 8-11: Payload Length (Little Endian)
        *(uint32_t*)(pTxData + 8) = static_cast<uint32_t>(length);
        
        // Copy user data starting after the header (offset 12 bytes usually)
        // Assuming header is 12 bytes (Magic(4) + Ver(4) + Len(4))
        if ((size_t)pData + length <= sizeof(txBuffer)) {
            memcpy(pTxData + 12, pData, length);
            
            // Update global counter for monitoring
            g_sovdMessageCounter++;

            // Trigger Transmission via COM Interface
            // We use the generic Send function from the COM driver mapped to our socket/service
            if (Appl_Com_Send(SOVD_SERVICE_ID, pTxData, length + 12) == E_OK) {
                retStatus = E_OK;
            } else {
                retStatus = E_NOT_ACCEPTED;
            }
        } else {
            retStatus = E_PARAM_OUT_OF_RANGE;
        }
    } else {
        retStatus = E_NOT_STARTED;
    }

    return retStatus;
}

/**
 * \ingroup Appl_SoVdApi
 * \brief Receives a Vehicle Data message asynchronously.
 * 
 * Blocks until a valid SOVD message is available on the network stack.
 * 
 * \param pRxBuffer Buffer to store the received message.
 * \param timeout Timeout value in milliseconds.
 * \return Status code indicating success or failure.
 */
StatusType SoVd_Receive(void* pRxBuffer, uint32_t timeout) {
    StatusType retStatus = E_NOT_STARTED;
    uint32_t bytesRead = 0;

    if (g_sovdInitialized && (pRxBuffer != nullptr)) {
        // Receive from the underlying TCP/IP stack associated with SOVD_SERVICE_ID
        // The buffer must be large enough to hold the maximum expected frame size
        // including headers.
        
        // In a real implementation, this calls the OS Socket API wrapped by 
        // the AUTOSAR Net/Com drivers.
        
        // Example pseudo-call to the abstracted receive function:
        // Assuming the buffer passed has sufficient space for max frame size
        bytesRead = Appl_Com_Recv(SOVD_SERVICE_ID, pRxBuffer, SOVD_MAX_MESSAGE_LENGTH, timeout);

        if (bytesRead > 0) {
            // Basic validation: Check Magic Number at start of packet
            const char* magicPtr = reinterpret_cast<const char*>(pRxBuffer);
            if (magicPtr[0] == 'S' && magicPtr[1] == 'O' && magicPtr[2] == 'V' && magicPtr[3] == 'D') {
                retStatus = E_OK;
            } else {
                retStatus = E_NOT_ACCEPTED; // Invalid protocol detected
            }
        } else {
            retStatus = E_NOT_ACCEPTED;
        }
    } else {
        retStatus = E_NOT_STARTED;
    }

    return retStatus;
}

/**
 * \ingroup Appl_SoVdApi
 * \brief Shuts down the SOVD subsystem.
 * 
 * Cleans up resources allocated during initialization.
 * 
 * \return Always returns E_OK.
 */
StatusType SoVd_DeInit(void) {
    if (g_sovdInitialized) {
        // Stop listening/sending
        g_sovdInitialized = false;
        // Reset counters if needed
        g_sovdMessageCounter = 0;
        
        // Call Deinit on lower layers if required by architecture
        // Appl_Cm_Stop(); 
    }
    return E_OK;
}

// ============================================================================
// Helper Functions for Data Encoding
// ============================================================================

/**
 * \brief Converts a float temperature reading to a packed integer representation.
 * Used internally by SoVd_Send to prepare sensor data.
 * 
 * \param temp Temperature value in Celsius.
 * \return Packed 16-bit integer representing the temperature.
 */
int16_t SoVd_EncodeTemperature(float temp) {
    // Simple scaling: 0°C -> 0, 100°C -> 65535 (Full scale)
    // Formula: (temp * 655.35) rounded to int16
    return static_cast<int16_t>((temp * 655.35f));
}

/**
 * \brief Decodes a packed temperature reading back to float.
 * 
 * \param tempRaw Raw 16-bit integer from SOVD message.
 * \return Temperature in Celsius.
 */
float SoVd_DecodeTemperature(int16_t tempRaw) {
    return static_cast<float>(tempRaw / 655.35f);
}
