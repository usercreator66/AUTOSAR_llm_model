/**
 * \file canif_cfg.h
 * 
 * \brief Configuration header file for CAN Interface (CanIf) module.
 * 
 * This file defines configuration parameters required by the CanIf module 
 * within the AUTOSAR Classic Platform. It includes settings for communication 
 * modes, data rates, error handling thresholds, and buffer configurations.
 * 
 * \note This is a generated configuration file based on standard AUTOSAR 
 *       Classic Platform conventions. Actual values should be adjusted to 
 *       match specific project requirements and hardware capabilities.
 */

#ifndef CANIF_CFG_H
#define CANIF_CFG_H

/* ============================================================================
   INCLUDES
   ========================================================================== */

#include "Std_Types.h"
#include "MemMap.h"
#include "Can_Dm.h" /* Contains DM-generated identifiers like CanIdType, etc. */

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
   MACROS AND DEFINES
   ========================================================================== */

/**
 * @brief Maximum number of CAN channels supported in this configuration.
 */
#define CANIF_MAX_CHANNELS ((uint8)2u)

/**
 * @brief Maximum size of the receive queue per channel.
 */
#define CANIF_RX_QUEUE_SIZE ((uint16)32u)

/**
 * @brief Maximum size of the transmit queue per channel.
 */
#define CANIF_TX_QUEUE_SIZE ((uint16)16u)

/**
 * @brief Default arbitration priority level.
 */
#define CANIF_DEFAULT_ARB_PRIORITY ((uint8)0x00u)

/**
 * @brief Default time segment 1 value (TSEG1).
 */
#define CANIF_DEFAULT_TIME_SEG_1 ((uint8)0x04u)

/**
 * @brief Default time segment 2 value (TSEG2).
 */
#define CANIF_DEFAULT_TIME_SEG_2 ((uint8)0x01u)

/**
 * @brief Default synchronization jump width (SJW).
 */
#define CANIF_DEFAULT_SJW ((uint8)0x01u)

/**
 * @brief Bit rate prescaler value.
 */
#define CANIF_BIT_RATE_PRESCALER ((uint8)0x01u)

/**
 * @brief Error active flag mask.
 */
#define CANIF_ERR_ACTIVE_MASK ((uint8)0x00u)

/**
 * @brief Error passive flag mask.
 */
#define CANIF_ERR_PASSIVE_MASK ((uint8)0xFFu)

/**
 * @brief Remote transmission request flag mask.
 */
#define CANIF_RTR_MASK ((uint8)0x00u)

/**
 * @brief Data frame type flag mask.
 */
#define CANIF_DATA_FRAME_MASK ((uint8)0x00u)

/**
 * @brief Extended frame format flag mask.
 */
#define CANIF_EXT_FRAME_FORMAT_MASK ((uint8)0x00u)

/**
 * @brief BRS (Bit Rate Switch) flag mask.
 */
#define CANIF_BRS_MASK ((uint8)0x00u)

/**
 * @brief IDE (Identifier Extension) flag mask.
 */
#define CANIF_IDE_MASK ((uint8)0x00u)

/**
 * @brief SRR (Single bit ReTransmit Request) flag mask.
 */
#define CANIF_SRR_MASK ((uint8)0x00u)

/**
 * @brief FMI (Frame Message Identifier) mask length.
 */
#define CANIF_FMI_LENGTH ((uint8)11u)

/* ============================================================================
   TYPE DEFINITIONS
   ========================================================================== */

/**
 * @brief Enumeration defining the CAN communication mode.
 */
typedef enum
{
    eCanMode_Normal = 0,
    eCanMode_LowPower = 1,
    eCanMode_Stby = 2,
    eCanMode_Mute = 3
} Can_Mode;

/**
 * @brief Enumeration defining the CAN bus state.
 */
typedef enum
{
    eCanBusState_Idle = 0,
    eCanBusState_TransmissionActive = 1,
    eCanBusState_ReceptionActive = 2,
    eCanBusState_ErrorPassive = 3,
    eCanBusState_ErrorActive = 4
} Can_BusState;

/**
 * @brief Structure representing a single CAN message identifier.
 */
typedef struct
{
    uint32 Id;           /**< Identifier field */
    uint8  Ide;          /**< Identifier Extension flag */
    uint8  Rtr;          /**< Remote Transmission Request flag */
    uint8  ExtId[11];     /**< Extended Identifier bits [29:18] */
    uint8  StdId[11];     /**< Standard Identifier bits [17:0] */
} Can_IdType;

/**
 * @brief Structure representing a CAN message with DLC information.
 */
typedef struct
{
    Can_IdType Id;        /**< Identifier structure */
    uint8  Dlc;           /**< Data Length Code */
    uint8  Data[8];       /**< Payload data array */
} Can_DataType;

/**
 * @brief Structure representing a CAN message ready for transmission.
 */
typedef struct
{
    Can_IdType Id;        /**< Identifier structure */
    uint8  Dlc;           /**< Data Length Code */
    uint8  Data[8];       /**< Payload data array */
    uint8  TxStatus;      /**< Transmission status */
} Can_MsgTxType;

/**
 * @brief Structure representing a received CAN message.
 */
typedef struct
{
    Can_IdType Id;        /**< Identifier structure */
    uint8  Dlc;           /**< Data Length Code */
    uint8  Data[8];       /**< Received payload data array */
    uint8  RxStatus;      /**< Reception status */
} Can_MsgRxType;

/**
 * @brief Structure containing global CAN interface configuration.
 */
typedef struct
{
    Can_Mode Mode;            /**< Communication mode selection */
    uint32 BitRate;           /**< Target bit rate in bps */
    uint8  TimeSeg1;          /**< Time Segment 1 value */
    uint8  TimeSeg2;          /**< Time Segment 2 value */
    uint8  SJW;               /**< Synchronization Jump Width */
    uint8  Prescaler;         /**< Clock prescaler value */
    uint8  MaxErrorCount;     /**< Maximum allowed error count before warning */
    uint8  WarningLimit;      /**< Limit for switching from Active to Passive */
    uint8  ErrorLimit;        /**< Limit for entering Bus Off state */
    uint8  WakeUpCounter;     /**< Counter for wake-up sequence */
    uint8  SleepCurrentLimit; /**< Current limit during sleep mode */
    uint8  LowPowerCurrentLimit; /**< Current limit during low power mode */
} Can_ConfigType;

/**
 * @brief Structure containing per-channel configuration.
 */
typedef struct
{
    uint8 ChannelIndex;       /**< Index of the configured channel */
    uint8 Enabled;            /**< Flag indicating if channel is enabled */
    uint8 PriorityLevel;      /**< Arbitration priority level */
    uint8 BufferSize;         /**< Size of RX/TX buffers for this channel */
} Can_ChannelConfigType;

/* ============================================================================
   FUNCTION PROTOTYPES
   ========================================================================== */

/**
 * \brief Initialize the CAN interface controller.
 * 
 * \param[in] Config Pointer to the configuration structure.
 * 
 * \return Status code indicating success or failure.
 */
void CanIf_Init(Can_ConfigType* Config);

/**
 * \brief Start the CAN interface controller.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_Start(void);

/**
 * \brief Stop the CAN interface controller.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_Stop(void);

/**
 * \brief Send a CAN message asynchronously.
 * 
 * \param[in] MsgPtr Pointer to the message to send.
 * \param[out] Status Pointer to store transmission status.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_SendMsgAsync(Can_MsgTxType* MsgPtr, uint8* Status);

/**
 * \brief Receive a CAN message synchronously.
 * 
 * \param[out] MsgPtr Pointer to the buffer where the message will be stored.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_ReceiveMsgSync(Can_MsgRxType* MsgPtr);

/**
 * \brief Check if a new message has arrived in the RX queue.
 * 
 * \return TRUE if a message is available, FALSE otherwise.
 */
Boolean CanIf_IsMessageAvailable(void);

/**
 * \brief Get the current bus state.
 * 
 * \return The current bus state enumeration.
 */
Can_BusState CanIf_GetBusState(void);

/**
 * \brief Reset the error counter.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_ResetErrorCounter(void);

/**
 * \brief Enter low power mode.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_EnterLowPowerMode(void);

/**
 * \brief Exit low power mode.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_ExitLowPowerMode(void);

/**
 * \brief Configure a specific CAN channel.
 * 
 * \param[in] ChannelIdx Index of the channel to configure.
 * \param[in] Config Pointer to the channel-specific configuration.
 * 
 * \return Status code indicating success or failure.
 */
Std_ReturnType CanIf_SetChannelCfg(uint8 ChannelIdx, Can_ChannelConfigType* Config);

/* ============================================================================
   END OF FILE
   ========================================================================== */

#ifdef __cplusplus
}
#endif

#endif /* CANIF_CFG_H */
