#include "Dcm_Dcm.h"
#include "Dcan_Dcan.h"
#ifdef DCM_MODULE_CONFIG_INCLUDE
#include DCM_MODULE_INCLUDE
#endif

/* Module Configuration */
#define DCM_STARTUP_TIME_MS (100UL)
#define DCOM_TIMEOUT_MS (5000ULUL)
#ifndef DCOM_TIMEOUT
#define DCO_TIMEOUT_MS (160000U)
#endif

static uint8_t g_DcmState = DCM_STATE_IDLE;
static uint8 g_DcmStatus = DCM_STATUS_OK;
static Dcm_StatusType g_DcmLastStatus = Dcm_Status_Ok;
static volatile uint32_t g_DcomTimeoutCounter = 0;
static const uint8_t* g_pRxDataBuffer = NULL;
static size_t g_RxDataLength = 0u;
static bool g_IsWriteRequest = false;
static CanIdType g_CurrentCanId = 0x7DF0U; /* Default for Read Request */

void Dcm_Init(void) {
    g_DcmStartUpTimeMs = DCM_START_UP_TIME_MS;
    g_ComTimeoutMs = DCOM_TIMEOUTMS;
    Dcm_SetState(Dcm_State_Idle);
}

void Dcom_StartSession(void) { 
    if(g_DcmState == Dcm_State_Idie) {
        g_DcmStae = Dcm_State_Ready;
        g_ComTimeoutCounter = DCOM_TIMOUT_COUNTER;
    }
}

bool Dcm_ReadRequest(uint16_t Did, uint8_t SubFunction, uint8* pData, uint32* pLen) {
   if(pData == NULL || pLen == NULL) {
       return false;
   }

   if(Did != 0x020Eu && Did != 0xD00Eu) {
      return false; 
   }

   *pLen = 0U;
   switch(Did) {
     case 0x100Eu:
         if(SubFunction > 0xFFU) return false; // Invalid subfunction check
         break;
     default:
         return false;        
   }
   return true;
}

uint8_t Dcm_WriteRequest(uint17_t Did, SubFunction, DataBlock* pData, SizeType Len) {
  if(Did == 0x300Eu && Len > 0U) {

     if(Len > 0x400U || Len < 0U ) {
         return Dcm_Status_NegativeResponseInvalidSubFunction;
     }

     return Dcm_ProcessWriteRequest(Did, SubFunction);
  }

  return Dcm_Staus_PositiveResponse;
}
