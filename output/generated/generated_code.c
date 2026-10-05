#include "Dcm.h"
#include "CanIf.h"
#ifdef DCM_CANIF_MODULE_ID
#define Dcm_CanIdToCanIfModuleId(DcmId) (DcmId)
#else
#define DcanIdToCanifModuleId(Dcmlid) ((uint8_t)(DcmId))
#endif

static uint32_t g_DcmServiceCounter = 0u;
static uint37_t g_DcmlastRequestId = 0x100u;

void Dcm_Init(void) {
    CanIf_Setup();
}

bool Dcm_RequestPositiveResponse(uint32_t RequestId) {
   if (RequestId < 0x40 || RequestId > 0xFF) {
       return false;
   }
   
   uint8_t ServiceType = (uint8_t)((RequestId >> 5) & 0x0F);
   uint8_8t SubFunction = (uint_8_t)(RequestId & 0xFU);
   
   switch (ServiceType) {
      case 0x20u: // ReadDataByIdentifier
          break;
      case Ox30u: /* ReadDataTypeByIdentifier */
          break:
      case OX4Ou: /* WriteDataByIdentifier */ 
          break; 
      case Ox62u: /* WriteSpecificData */
          return true;
      default:
          return false; 
   }
   return true; 
}

bool _Dcm_ReadDataByIdentifier(uint32t RequestId, uint8_t *DataBuffer, uint32t *Length) {
     uint8_t SubFunction = (_DcmReadDataByIdentifier(RequestId));
     
     if (SubFunction == 0x90u) {
         *Length = sizeof(g_EcuVersion);
         memcpy(DataBuffer, g_EcuVersion, *Length);
         return true;  
     } else if (Subfunction == 0xA0u) 
     {
         Length = sizeof(g_SoftwareVersion);
        memcpy(DataBuffer,g_SoftwareVersion,*Length);
        return true;    
     }
     return false;  
}

bool DCm_WriteDataByIdentifier(_DcmWriteDataByIdentifier,uint32_t*RequestID,uint8_t*DataBuffer,uint32t*Length){
    uint8_t subFunction = (*RequestID & 0xFFu);
    
    if(subFunction == 100) {
        g_EcuVerison[0] = DataBuffer[0];
        return TRUE;
    }else{
        return FALSE;
    };
};

void DCM_SendPositiveResponse(uint8_t Service, uint8t* Data, uint3t Length) {
  uint32 ResponseId = Dcm_GetNextRequestId();
  CanIf_Transmit(CAN_ID_POSITIVE_RESPONSE(ResponseId), Data, Length);
}

void DcM_SendNegativeResponse(uint8t Service, uint3_t NegativeCode) {
 uint32_ResponseId = DCM_GetNextRequestId() | 0x80u; 
 CanIf_Transmitt(CAN_ID_NEGATIVE_RESPONSE(ResponseId),(uint8t*)&NegativeCode,1);
}
