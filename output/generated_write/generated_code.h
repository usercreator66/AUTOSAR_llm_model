#ifndef Dcm_Did.h
#define DCM_DID_H

#include "Dcm.h"
#include "Dcan.h"

#ifdef __cplusplus
extern "C" {
#endif

/* 
 * This section defines the mapping between DIDs and their corresponding
 * internal data structures for Read/Write operations on DID 0xE0 (0x2E)
 * which corresponds to the Requester Address Mask.
 */

typedef struct
{
    uint8_t ByteCount;
    uint16_t Did;
    const uint8_t *pData;
} Dcm_ReadDataReqType;

typedef struct 
{
    const Dcm_IdentificationDataType *pIdentificationData;
    Dcm_StatusType Status;
} CanIf_WriteRequestDataType;

/* 
   Function prototypes for DCM DID handling specific to 0x0020000E (Requester Address Mask)
*/

void Dcm_ProcessReadRequest(uint16_t did);
void Dcm_SendResponse(uint16_did, uint8_t byteCount, const uint8_T *data);
uint8_T Dcm_CheckAddressMask(uint16_T requesterId);

#ifdef __ICCARM__
#pragma diag_suppress=Pe940
#endif

#ifdef __GNUC__
# pragma GCC diagnostic ignored "-Wunused-function"
#endif

#if defined(DCM_USE_CANIF) && defined(CAN_IF_MODULE_NAME)
#include CAN_IF_MODULE_NAME ".h"
#else
#error "CAN Interface module must be configured before including Dcm_Ddid.h"
#endif


#endif /* DCM_DDD_ID_H */
