Name:		sarif4k
Version:	0.6.0
Release:	1
Summary:	SARIF data models for Kotlinx serialization
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/detekt/sarif4k
# detekt/sarif4k commit 9be3911d5023f3a1db17bc6b13173fcc57a8f24a (0.6.0).
# Patch0 replaces JsonObject.serializer() with serializer<JsonObject>() so
# these sources compile against kotlinx-serialization 1.11.0.
Patch0:		sarif4k-serializer.patch
Source0:	sarif4k-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-21-openjdk-devel
BuildRequires:	kotlin = 2.0.21
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	kotlin-libs = 2.0.21
BuildRequires:	mvn(org.jetbrains.kotlinx:kotlinx-serialization-core) = 1.11.0
BuildRequires:	mvn(org.jetbrains.kotlinx:kotlinx-serialization-json) = 1.11.0

%description
io.github.detekt.sarif4k:sarif4k %{version}.
SARIF 2.1.0 data models compiled from commonMain with kotlinc 2.0.21
and the serialization compiler plugin. The JVM target is 1.8.
JsonObject.serializer() from serialization 1.4.1 is rewritten to
serializer<JsonObject>() for the published 1.11.0 runtime.

%prep
%autosetup -n sarif4k-%{version} -p1
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi
grep -F -q 'import kotlinx.serialization.serializer' src/commonMain/kotlin/io/github/detekt/sarif4k/SarifDataBindings.kt
if grep -F -q 'JsonObject.serializer()' src/commonMain/kotlin/io/github/detekt/sarif4k/SarifDataBindings.kt; then
	exit 1
fi

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
STDLIB=%{_javadir}/kotlin-stdlib.jar
CORE=%{_javadir}/kotlinx-serialization-core.jar
JSON=%{_javadir}/kotlinx-serialization-json.jar
PLUGIN=/usr/share/kotlin/lib/kotlinx-serialization-compiler-plugin.jar
test -s "$STDLIB"
test -s "$CORE"
test -s "$JSON"
test -s "$PLUGIN"
mkdir -p classes
find src/commonMain -name '*.kt' | sort > sources.list
test "$(wc -l < sources.list)" -eq 4
kotlinc -J-Xmx2g -jvm-target 1.8 -language-version 2.0 -no-stdlib \
	-jdk-home "$JAVA_HOME" \
	-Xplugin="$PLUGIN" \
	-opt-in=kotlinx.serialization.ExperimentalSerializationApi \
	-opt-in=kotlinx.serialization.InternalSerializationApi \
	-cp "$STDLIB:$CORE:$JSON" -d classes @sources.list
test -s classes/io/github/detekt/sarif4k/SarifSerializer.class
test -s classes/io/github/detekt/sarif4k/Merging.class
test -s classes/io/github/detekt/sarif4k/SarifSchema210.class
printf '%s\n' 'Manifest-Version: 1.0' 'Automatic-Module-Name: io.github.detekt.sarif4k' > manifest.mf
jar cfm sarif4k.jar manifest.mf -C classes .
jar i sarif4k.jar
desc=$(jar --describe-module --file sarif4k.jar)
printf '%s\n' "$desc"
if printf '%s\n' "$desc" | grep -F -q 'Unable'; then
	exit 1
fi
printf '%s\n' "$desc" | grep -F -qx 'io.github.detekt.sarif4k automatic'
cat > sarif4k.pom << END
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>io.github.detekt.sarif4k</groupId>
  <artifactId>sarif4k</artifactId>
  <version>%{version}</version>
  <name>sarif4k</name>
  <description>SARIF data models for Kotlinx serialization</description>
  <url>https://github.com/detekt/sarif4k</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.jetbrains.kotlin</groupId>
      <artifactId>kotlin-stdlib</artifactId>
      <version>2.0.21</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlinx</groupId>
      <artifactId>kotlinx-serialization-core</artifactId>
      <version>1.11.0</version>
    </dependency>
    <dependency>
      <groupId>org.jetbrains.kotlinx</groupId>
      <artifactId>kotlinx-serialization-json</artifactId>
      <version>1.11.0</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact sarif4k.pom:sarif4k.jar \
	--file-name sarif4k \
	--filelist .mfiles
idx="%{buildroot}/usr/share/sysjar/index/io.github.detekt.sarif4k/sarif4k.sysjar"
test -s "$idx"
grep -F -q '"version": "%{version}"' "$idx"
grep -F -q '"artifactId": "sarif4k"' "$idx"
test -s %{buildroot}%{_javadir}/sarif4k.jar

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-21-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
JAR=%{buildroot}%{_javadir}/sarif4k.jar
STDLIB=%{_javadir}/kotlin-stdlib.jar
CORE=%{_javadir}/kotlinx-serialization-core.jar
JSON=%{_javadir}/kotlinx-serialization-json.jar
test -s "$JAR"
mkdir -p check
cat > check/Probe.kt << 'EOF'
import io.github.detekt.sarif4k.SarifSerializer
import io.github.detekt.sarif4k.merge

fun main() {
val parsed = SarifSerializer.fromJson(
"""{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"detekt"}}}]}"""
)
val merged = parsed.merge(parsed)
val name = parsed.runs.single().tool.driver.name
if (name != "detekt" || parsed.version.value != "2.1.0" || merged.runs.size != 1) {
error("sarif check failed")
}
println("sarif4k_ok " + name + " " + parsed.version.value)
}
EOF
kotlinc -J-Xmx1g -jvm-target 1.8 -language-version 2.0 -no-stdlib \
	-jdk-home "$JAVA_HOME" \
	-cp "$JAR:$STDLIB:$CORE:$JSON" -d check/out check/Probe.kt
java -cp "check/out:$JAR:$STDLIB:$CORE:$JSON" ProbeKt > check/out.txt
cat check/out.txt
grep -F -qx 'sarif4k_ok detekt 2.1.0' check/out.txt

%files -f .mfiles
%license LICENSE
