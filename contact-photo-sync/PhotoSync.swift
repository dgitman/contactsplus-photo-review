import Foundation
import Contacts
import ImageIO
import CryptoKit

struct Entry:Codable { let identifier:String;let email:String;let givenName:String;let familyName:String;let imagePath:String }
struct Manifest:Codable { let entries:[Entry] }
struct SyncFailure:Error,CustomStringConvertible { let description:String }
func hash(_ data:Data?) -> String? { data.map { SHA256.hash(data:$0).map {String(format:"%02x",$0)}.joined() } }
let args=CommandLine.arguments
let apply=args.contains("--apply")
func arg(_ key:String)->String? { guard let i=args.firstIndex(of:key),i+1<args.count else{return nil};return args[i+1] }
let base=URL(fileURLWithPath:arg("--output") ?? "outputs/contact-photo-recovery/background-test",isDirectory:true)
try FileManager.default.createDirectory(at:base,withIntermediateDirectories:true)
var stage="startup"
func event(_ value:[String:Any]) {
 var v=value;v["stage"]=stage;v["at"]=ISO8601DateFormatter().string(from:Date())
 if let d=try? JSONSerialization.data(withJSONObject:v,options:[.sortedKeys]),let s=String(data:d,encoding:.utf8){print(s);fflush(stdout)}
}
do {
 if args.contains("--authorize") {
  stage="authorization"
  let store=CNContactStore()
  if CNContactStore.authorizationStatus(for:.contacts) == .authorized {event(["status":"authorized"]);exit(0)}
  var completed=false;var granted=false;var failure:String?=nil
  store.requestAccess(for:.contacts){ok,error in DispatchQueue.main.async{granted=ok;failure=error.map{String(describing:$0)};completed=true}}
  let deadline=Date().addingTimeInterval(60)
  while !completed && Date()<deadline {RunLoop.main.run(until:Date().addingTimeInterval(0.1))}
  event(["status":granted ? "authorized" : "not_authorized","error":failure as Any? ?? NSNull()]);exit(granted ? 0 : 2)
 }
 guard let path=arg("--manifest") else {throw SyncFailure(description:"Required: --manifest PATH [--apply] [--output DIR]. Default is dry-run.")}
 let manifest=try JSONDecoder().decode(Manifest.self,from:Data(contentsOf:URL(fileURLWithPath:path)))
 guard !manifest.entries.isEmpty,manifest.entries.count<=10,Set(manifest.entries.map{$0.identifier}).count==manifest.entries.count else{throw SyncFailure(description:"Manifest must contain 1–10 distinct contacts")}
 let store=CNContactStore();stage="authorization";event(["status":CNContactStore.authorizationStatus(for:.contacts).rawValue,"apply":apply])
 guard CNContactStore.authorizationStatus(for:.contacts) == .authorized else {throw SyncFailure(description:"Full Contacts permission is required for this executable; no changes attempted")}
 let keys=[CNContactIdentifierKey,CNContactGivenNameKey,CNContactFamilyNameKey,CNContactEmailAddressesKey,CNContactImageDataKey,CNContactThumbnailImageDataKey].map{$0 as CNKeyDescriptor}
 var planned:[(Entry,CNContact,Data)]=[]
 for e in manifest.entries {
  stage="decode_image";let data=try Data(contentsOf:URL(fileURLWithPath:e.imagePath));guard let source=CGImageSourceCreateWithData(data as CFData,nil),CGImageSourceCreateImageAtIndex(source,0,nil) != nil else{throw SyncFailure(description:"Image failed to decode for \(e.identifier)")}
  stage="fetch_exact_contact";event(["identifier":e.identifier]);let request=CNContactFetchRequest(keysToFetch:keys);request.unifyResults=false;request.predicate=CNContact.predicateForContacts(withIdentifiers:[e.identifier]);var cs:[CNContact]=[];try store.enumerateContacts(with:request){c,_ in cs.append(c)}
  guard cs.count==1,let c=cs.first,c.givenName==e.givenName,c.familyName==e.familyName,c.emailAddresses.contains(where:{($0.value as String).lowercased()==e.email.lowercased()}) else{throw SyncFailure(description:"Contact identity no longer matches manifest")}
  stage="check_unique_email";let req=CNContactFetchRequest(keysToFetch:[CNContactIdentifierKey as CNKeyDescriptor,CNContactEmailAddressesKey as CNKeyDescriptor]);req.unifyResults=false;var matches=Set<String>();try store.enumerateContacts(with:req){c,_ in if c.emailAddresses.contains(where:{($0.value as String).lowercased()==e.email.lowercased()}){matches.insert(c.identifier)}};guard matches==Set([c.identifier]) else{throw SyncFailure(description:"Email is not unique")}
  stage="backup_image";let old=c.imageData;let oldThumb=c.thumbnailImageData
  if let old=old{try old.write(to:base.appendingPathComponent(c.identifier+".original-image"),options:.atomic)}
  if let oldThumb=oldThumb{try oldThumb.write(to:base.appendingPathComponent(c.identifier+".original-thumbnail"),options:.atomic)}
  let meta:[String:Any]=["identifier":c.identifier,"email":e.email,"imageWasAbsent":old==nil,"previousSHA256":hash(old) as Any? ?? NSNull(),"candidateSHA256":hash(data)!]
  try JSONSerialization.data(withJSONObject:meta,options:.prettyPrinted).write(to:base.appendingPathComponent(c.identifier+".json"),options:.atomic)
  if old != nil {event(["identifier":c.identifier,"status":"skipped_existing_photo"]);continue}
  planned.append((e,c,data));event(["identifier":c.identifier,"status":"prepared","bytes":data.count])
 }
 guard apply else{stage="complete";event(["status":"dry_run_complete","prepared":planned.count,"modified":0]);exit(0)}
 var saved=0
 for (e,c,data) in planned {
  stage="refetch_before_save";let fresh=try store.unifiedContact(withIdentifier:c.identifier,keysToFetch:keys);guard fresh.imageData==nil,fresh.givenName==e.givenName,fresh.familyName==e.familyName,Set(fresh.emailAddresses.map{$0.value as String})==Set(c.emailAddresses.map{$0.value as String}) else{throw SyncFailure(description:"Contact changed after preparation")}
  stage="save_photo";event(["identifier":c.identifier]);let changed=fresh.mutableCopy() as! CNMutableContact;changed.imageData=data;let request=CNSaveRequest();request.update(changed);try store.execute(request);saved+=1
  stage="verify_photo";let result=try store.unifiedContact(withIdentifier:c.identifier,keysToFetch:keys);guard let actual=result.imageData,let src=CGImageSourceCreateWithData(actual as CFData,nil),CGImageSourceCreateImageAtIndex(src,0,nil) != nil,result.thumbnailImageData != nil else{throw SyncFailure(description:"Save returned but readable image/thumbnail not verified")}
  event(["identifier":c.identifier,"status":"saved_and_verified","fullBytes":actual.count,"thumbnailBytes":result.thumbnailImageData!.count])
 }
 stage="complete";event(["status":"complete","modified":saved])
}catch{event(["status":"failed","error":String(describing:error)]);exit(1)}
