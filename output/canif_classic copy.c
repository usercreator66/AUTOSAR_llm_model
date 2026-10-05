/**
 * \file CanIf_RxIndication.c
 *
 * \brief
 *   Implementation of the CAN Interface (CanIf) Rx Indication function.
 *   This file contains the implementation of the public API function 
 *   `CanIf_RxIndication` as specified in the AUTOSAR Classic Platform 
 *   Software Specification for the CanIf module.
 *
 * \version
 *   4.0.0
 *
 * \copyright
 *   Copyright (c) 2019-2023, Open Source Automotive Consortium.
 *   All rights reserved.
 */

/*
 * ============================================================================
 * DISCLAIMER
 * ============================================================================
 * THIS FILE IS GENERATED FROM THE AUTOSAR CLASSIC PLATFORM SOFTWARE SPECIFICATION.
 * ANY CHANGES MADE TO THIS FILE WILL BE OVERWRITTEN DURING THE NEXT BUILD/GENERATION CYCLE.
 * PLEASE MODIFY THE CORRESPONDING CONFIGURATION SETTINGS IN THE AUTOSAR TOOLCHAIN
 * OR THE SPECIFICATION DOCUMENTS IF CUSTOMIZATION IS REQUIRED.
 */


#include "CanIf_Internal.h"
#include "CanIf_ProtocolStack.h"
#include "CanIf_Cfg.h"
#include "Can_Dm.h"
#include "CanIf_SecMgmt.h" /* Only if SecMgmt is enabled via configuration */
#include <string.h>       /* For memcpy, memset */


#if defined(CANIF_SEC_MGMT_ENABLED) && (CANIF_SEC_MGMT_ENABLED == STD_TRUE)
    #include "SecMgmt.h"
#endif


/*
 * ============================================================================
 * Module Global Variables
 * ============================================================================
 */

#if defined(CANIF_USE_RX_INDICATION_CALLBACK) && (CANIF_USE_RX_INDICATION_CALLBACK == STD_TRUE)
    /**
     * \var
     *   Pointer to the callback function registered by the application layer.
     *   Used when the application requests a callback instead of using the standard
     *   notification mechanism.
     *
     * \note
     *   This variable is only present if the configuration option 
     *   `CANIF_USE_RX_INDICATION_CALLBACK` is set to TRUE.
     */
    CanIf_RxCallbackType CanIf_RxCb;
#endif


/*
 * ============================================================================
 * Function Definitions
 * ============================================================================
 */

/**
 * \ingroup CanIfApi
 * \defgroup CanIfRxIndicationGroup Rx Indication Group
 * \{
 */


/**
 * \pagefunc CanIf_RxIndication
 *
 * \brief
 *   This function handles the reception of a CAN message from the Bus Controller.
 *   It performs security checks (if enabled), updates internal state counters,
 *   and notifies the Application Layer.
 *
 * \param [in] Idx
 *   Index of the CAN channel receiving the message.
 *
 * \param [in] IfId
 *   Identifier of the received CAN frame (Standard or Extended).
 *
 * \param [in] Len
 *   Length of the data payload in bytes.
 *
 * \param [in] Data
 *   Pointer to the buffer containing the received data bytes.
 *
 * \return
 *   - E_OK      : If the indication was processed successfully.
 *   - E_NOT_OK  : If an error occurred during processing (e.g., invalid index).
 *
 * \details
 *   The function logic follows these steps:
 *   1. Validate input parameters against configuration limits.
 *   2. Perform Security Management check (if enabled).
 *   3. Update Receive Counter statistics.
 *   4. Call the Application Callback with the received data.
 *   5. Return status.
 */
Std_ReturnType CanIf_RxIndication(
    CanIf_ChannelIdType Idx,
    Std_UINT32          IfId,
    uint8               Len,
    const uint8         *Data
)
{
    Std_ReturnType ret = E_OK;
    CanIf_StatusType  Status;
    CanIf_ChInfoType* pChInfo;
    
    /*
     * Step 1: Parameter Validation & Initialization
     */
    
    /* Check Channel Validity */
    if ((Idx >= CanIf_NumOfChannels) || (Idx < 0))
    {
        return E_NOT_OK;
    }

    /* Retrieve Channel Information Structure */
    pChInfo = CanIf_GetChannelInfo(Idx);
    
    /* Initialize Status based on channel configuration */
    Status = pChInfo->Status;

    /*
     * Step 2: Security Management Check (Conditional Compilation)
     * 
     * If Security Management is enabled, we must verify that the message
     * has passed authentication before notifying the application.
     */
#if defined(CANIF_SEC_MGMT_ENABLED) && (CANIF_SEC_MGMT_ENABLED == STD_TRUE)
    {
        CanIf_SecMgmtResultType SecResult;
        
        /* Perform Authentication Check */
        SecResult = CanIf_SecMgmt_AuthenticateMessage(Idx, IfId, Data, Len);
        
        if (SecResult != SEC_MGM_AUTH_SUCCESSFUL)
        {
            /* Message failed authentication. Discard without notifying App. */
            /* Optionally log error here depending on implementation details */
            return E_NOT_OK;
        }
    }
#else
    /* No security check required for this build variant */
#endif


    /*
     * Step 3: Update Internal State Counters
     * 
     * Increment the receive counter for the specific channel.
     */
    CanIf_IncrementRxCounter(pChInfo);


    /*
     * Step 4: Notify Application Layer
     * 
     * Depending on the configuration, either call the global callback 
     * or the per-channel callback.
     */
#if defined(CANIF_USE_RX_INDICATION_CALLBACK) && (CANIF_USE_RX_INDICATION_CALLBACK == STD_TRUE)
    {
        /* Use the globally configured callback pointer if available */
        if (CanIf_RxCb != NULL_PTR)
        {
            CanIf_RxCb(Idx, IfId, Len, Data);
        }
        else
        {
            /* Fallback behavior if callback is null but feature is enabled:
             * Typically implies no action or default handling defined in spec.
             * Here we assume strict adherence means do nothing if callback missing.
             */
            /* In some implementations, a static dummy might be used, 
             * but strictly following 'use callback' usually implies checking existence. */
            /* For robustness, we might still update stats even if callback fails,
             * which is handled above. We proceed assuming valid callback exists 
             * if the flag is true, or handle gracefully below. */
            
            /* NOTE: If the spec requires a fallback when callback is NULL despite 
             *       the flag being TRUE, implement it here. Otherwise, return OK. */
            ret = E_OK; 
        }
    }
#else
    {
        /* Standard Notification Mechanism (Non-Callback style)
         * Called directly by the Bus Controller driver upon successful reception.
         */
        CanIf_Notification_Received(Idx, IfId, Len, Data);
        ret = E_OK;
    }
#endif


    /*
     * Step 5: Finalize
     */
    return ret;
}


/**
 * \endgroup
 * \endsection
 */


/*
 * ============================================================================
 * End of File
 * ============================================================================
 */
